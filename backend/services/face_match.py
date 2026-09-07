"""Face match / identity similarity using real face embeddings.

Images are processed in memory. Embeddings are not logged, returned, or saved.
"""
import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

from backend.services.image_analysis import decode_image
from backend.services.liveness import analyze_liveness_sequence
from backend.services.model_runtime import MODEL_LOAD_LOCK

MODEL_NAME = "facenet-pytorch InceptionResnetV1 pretrained on VGGFace2"
METRIC = "cosine_similarity"
FACENET_WEIGHTS_FILENAME = "20180402-114759-vggface2.pt"

# Initial FaceNet cosine thresholds. These must be calibrated with a
# representative validation set before production use.
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.78"))
FACE_REVIEW_THRESHOLD = float(os.getenv("FACE_REVIEW_THRESHOLD", "0.62"))
MIN_FACE_IMAGE_SIDE = 160


class FaceMatchError(ValueError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class FaceEmbeddingResult:
    face_count: int
    embedding: np.ndarray | None = None
    box: list[float] | None = None


@lru_cache(maxsize=1)
def load_face_models():
    """Load detector and FaceNet once per process.

    FaceNet was selected because it is a local PyTorch face-embedding model and
    is more compatible with this Windows/Python setup than dlib-based packages.
    """
    with MODEL_LOAD_LOCK:
        from facenet_pytorch import InceptionResnetV1, MTCNN

        torch.set_num_threads(min(4, torch.get_num_threads()))
        checkpoint = Path(torch.hub.get_dir()).parent / "checkpoints" / FACENET_WEIGHTS_FILENAME
        if not checkpoint.exists():
            raise FaceMatchError(
                "MODEL_UNAVAILABLE",
                "FaceNet weights are not installed yet. Run: python -m backend.training.setup_face_match",
            )
        detector = MTCNN(image_size=160, margin=20, keep_all=True, device="cpu")
        embedder = InceptionResnetV1(pretrained="vggface2").eval()
        return detector, embedder


def _error(status: str, message: str) -> dict:
    return {"success": False, "status": status, "message": message}


def _decode_for_match(contents: bytes, label: str):
    try:
        image, metadata = decode_image(contents)
    except ValueError as exc:
        raise FaceMatchError("INVALID_IMAGE", f"{label}: {exc}") from exc
    if min(image.size) < MIN_FACE_IMAGE_SIDE:
        raise FaceMatchError("IMAGE_TOO_SMALL", f"{label}: use an image at least {MIN_FACE_IMAGE_SIDE}px wide and tall.")
    return image, metadata


def detect_face_embedding(image) -> FaceEmbeddingResult:
    detector, embedder = load_face_models()
    boxes, probabilities = detector.detect(image)
    if boxes is None or len(boxes) == 0:
        return FaceEmbeddingResult(face_count=0)
    confident = [
        (box, prob)
        for box, prob in zip(boxes, probabilities)
        if prob is not None and float(prob) >= 0.9
    ]
    if len(confident) != 1:
        return FaceEmbeddingResult(face_count=len(confident))
    face_tensor = detector.extract(image, [confident[0][0]], save_path=None)
    if face_tensor is None or len(face_tensor) != 1:
        return FaceEmbeddingResult(face_count=0)
    with torch.inference_mode():
        embedding = embedder(face_tensor).detach().cpu().numpy()[0].astype("float32")
    norm = float(np.linalg.norm(embedding))
    if not math.isfinite(norm) or norm <= 0:
        raise FaceMatchError("MODEL_ERROR", "The face model returned an invalid embedding.")
    embedding = embedding / norm
    return FaceEmbeddingResult(face_count=1, embedding=embedding, box=[float(value) for value in confident[0][0]])


def _validate_face(result: FaceEmbeddingResult, role: str):
    if result.face_count == 0:
        raise FaceMatchError("NO_FACE", f"No face detected in the {role} image.")
    if result.face_count > 1:
        raise FaceMatchError("MULTIPLE_FACES", f"Multiple faces detected in the {role} image.")
    if result.embedding is None:
        raise FaceMatchError("MODEL_ERROR", f"Could not generate a face embedding for the {role} image.")


def _decision(similarity: float) -> tuple[str, str, str]:
    if similarity >= FACE_MATCH_THRESHOLD:
        return "MATCH", "LOW", "The faces are highly similar. Face match alone does not prove legal identity."
    if similarity >= FACE_REVIEW_THRESHOLD:
        return "REVIEW", "MEDIUM", "Face similarity is inconclusive. Additional verification is recommended."
    return "MISMATCH", "HIGH", "Face mismatch detected. Additional verification is recommended."


def _assess_selfie_liveness(selfie_image, live_frame_bytes):
    frame_images = []
    for frame_bytes in live_frame_bytes or []:
        frame_image, _ = _decode_for_match(frame_bytes, "Live selfie frame")
        frame_images.append(frame_image)
    return analyze_liveness_sequence(frame_images or [selfie_image])


def _apply_liveness_to_decision(decision: str, risk_level: str, message: str, liveness: dict) -> tuple[str, str, str]:
    if decision != "MATCH":
        return decision, risk_level, message
    if liveness.get("live_confirmed"):
        return decision, risk_level, message + " Live selfie presence was confirmed."
    return (
        "REVIEW",
        "MEDIUM",
        message
        + " Face similarity matched, but live selfie presence was not confirmed; treat this as uncertain because it may be a phone-screen or printed-photo replay.",
    )


def compare_faces(reference_bytes: bytes, selfie_bytes: bytes, live_frame_bytes=None) -> dict:
    try:
        reference_image, _ = _decode_for_match(reference_bytes, "Reference image")
        selfie_image, _ = _decode_for_match(selfie_bytes, "Selfie image")
        reference = detect_face_embedding(reference_image)
        selfie = detect_face_embedding(selfie_image)
        _validate_face(reference, "reference")
        _validate_face(selfie, "selfie")
        similarity = float(np.dot(reference.embedding, selfie.embedding))
        if not math.isfinite(similarity):
            raise FaceMatchError("MODEL_ERROR", "The face model returned an invalid similarity score.")
        similarity = max(-1.0, min(1.0, similarity))
        decision, risk_level, message = _decision(similarity)
        liveness = _assess_selfie_liveness(selfie_image, live_frame_bytes)
        decision, risk_level, message = _apply_liveness_to_decision(decision, risk_level, message, liveness)
        display_score = round(max(0.0, min(1.0, (similarity + 1.0) / 2.0)) * 100, 1)
        return {
            "success": True,
            "reference_face_detected": True,
            "selfie_face_detected": True,
            "reference_face_count": reference.face_count,
            "selfie_face_count": selfie.face_count,
            "similarity": round(similarity, 4),
            "match_score": display_score,
            "decision": decision,
            "risk_level": risk_level,
            "message": message,
            "liveness": liveness,
            "details": {
                "model": MODEL_NAME,
                "metric": METRIC,
                "thresholds": {"match": FACE_MATCH_THRESHOLD, "review": FACE_REVIEW_THRESHOLD},
                "score_transform": "match_score = clamp((cosine_similarity + 1) / 2, 0, 1) * 100 for display only; it is not a calibrated identity probability.",
                "privacy": "Images and embeddings are processed in memory and are not saved or returned.",
            },
        }
    except FaceMatchError as exc:
        return _error(exc.status, exc.message)
    except Exception:
        logging.getLogger(__name__).exception("Face match failed")
        return _error("MODEL_UNAVAILABLE", "The face recognition model could not run.")
