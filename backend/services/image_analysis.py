"""Image classification with measured observations and no filename verdict overrides."""
import hashlib
import math
import concurrent.futures
import time
from collections import Counter
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from backend.services.model_runtime import MODEL_LOAD_LOCK

LOCAL_DETECTOR_PATH = Path(__file__).resolve().parents[1] / "models" / "visual_ai_detector.joblib"
DOMAIN_DETECTOR_PATH = Path(__file__).resolve().parents[1] / "models" / "siglip_domain"
FEEDBACK_DIR = Path(__file__).resolve().parents[1] / "data" / "feedback"
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
IDENTITY_CONTEXT_KEYWORDS = {
    "aadhar", "aadhaar", "adhar", "passport", "id", "identity", "card", "document",
    "license", "licence", "pan", "marks", "certificate", "undertaking", "affidavit",
}
PHOTO_PROMPTS = [
    "a real camera photograph of a person",
    "a real smartphone photo of a human",
    "a passport photo or identity photo captured by a camera",
]
SYNTHETIC_PROMPTS = [
    "a synthetic AI generated illustration of a person",
    "a 3D cartoon render of a person",
    "a computer generated portrait, not a real camera photo",
]
DETECTOR_TIMEOUT_SECONDS = 15
DOMAIN_TIMEOUT_SECONDS = 8
LIVENESS_TIMEOUT_SECONDS = 7
IMAGE_MODEL_BUDGET_SECONDS = 20
RUNTIME_REVIEW_THRESHOLDS = {
    "likely_genuine_max_ai_probability": 0.5,
    "likely_ai_min_ai_probability": 0.5,
}
AI_EVIDENCE_OVERRIDES_ID_REVIEW_MIN_PROBABILITY = 0.5
_analysis_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def decode_image(contents):
    if not contents or len(contents) > 10 * 1024 * 1024:
        raise ValueError("Choose a nonempty image smaller than 10 MB.")
    try:
        with Image.open(BytesIO(contents)) as source:
            if source.format not in SUPPORTED_FORMATS:
                raise ValueError("Only JPEG, PNG and WebP images are supported.")
            if source.width * source.height > 25_000_000:
                raise ValueError("Choose an image with fewer than 25 million pixels.")
            metadata = {"format": source.format, "has_exif": bool(source.getexif()),
                        "has_png_text": bool(getattr(source, "text", {})),
                        "size_bytes": len(contents)}
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            metadata.update(width=image.width, height=image.height)
            return image, metadata
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The image is damaged or cannot be decoded.") from exc


@lru_cache(maxsize=1)
def _load_visual_detector():
    import joblib
    with MODEL_LOAD_LOCK:
        import torch
        from torchvision import models

        torch.set_num_threads(min(4, torch.get_num_threads()))
        artifact = joblib.load(LOCAL_DETECTOR_PATH)
        key = artifact.get("training_summary", {}).get("feature_model_key", "mobilenet_v3_small")
        if key == "efficientnet_b0":
            weights = models.EfficientNet_B0_Weights.DEFAULT
            model = models.efficientnet_b0(weights=weights)
        elif key == "mobilenet_v3_small":
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            model = models.mobilenet_v3_small(weights=weights)
        else:
            raise ValueError(f"Unsupported feature extractor: {key}")
        model.classifier = torch.nn.Identity()
        model.eval()
        if list(artifact["classifier"].classes_) != [0, 1]:
            raise ValueError("Detector label mapping must be 0=real, 1=AI.")
        return model, weights.transforms(), artifact


def predict(image):
    import torch
    model, transform, artifact = _load_visual_detector()
    with torch.inference_mode():
        features = model(transform(image).unsqueeze(0)).cpu().numpy()
    probability = float(artifact["classifier"].predict_proba(features)[0, 1])
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Detector returned an invalid probability.")
    return probability, artifact.get("training_summary", {})


@lru_cache(maxsize=1)
def _load_domain_detector():
    with MODEL_LOAD_LOCK:
        import torch
        from transformers import AutoModel, AutoProcessor

        torch.set_num_threads(min(4, torch.get_num_threads()))
        processor = AutoProcessor.from_pretrained(DOMAIN_DETECTOR_PATH, local_files_only=True)
        model = AutoModel.from_pretrained(
            DOMAIN_DETECTOR_PATH,
            local_files_only=True,
            use_safetensors=True,
            trust_remote_code=False,
        ).eval()
        text_inputs = processor(
            text=PHOTO_PROMPTS + SYNTHETIC_PROMPTS,
            padding="max_length",
            return_tensors="pt",
        )
        return model, processor, text_inputs


def predict_synthetic_domain(image):
    import torch

    model, processor, text_inputs = _load_domain_detector()
    image_inputs = processor(images=[image], return_tensors="pt")
    with torch.inference_mode():
        scores = model(**image_inputs, **text_inputs).logits_per_image.softmax(dim=1)[0]
    photo_score = scores[:len(PHOTO_PROMPTS)].sum()
    synthetic_score = scores[len(PHOTO_PROMPTS):].sum()
    probability = float(synthetic_score / (photo_score + synthetic_score))
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Domain detector returned an invalid probability.")
    return probability, {
        "model_id": "google/siglip-base-patch16-224",
        "revision": "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed",
        "thresholds": {"high_synthetic_min_probability": 0.98},
    }


def _run_with_timeout(func, timeout_seconds, *args):
    future = _analysis_executor.submit(func, *args)
    return future.result(timeout=timeout_seconds)


def _remaining_timeout(deadline, max_timeout):
    return max(0.01, min(max_timeout, deadline - time.monotonic()))


def _has_identity_upload_context(filename: str | None, metadata: dict) -> bool:
    name = (filename or "").lower()
    tokens = {part for part in name.replace("-", " ").replace("_", " ").replace(".", " ").split() if part}
    return bool(tokens & IDENTITY_CONTEXT_KEYWORDS)


def fuse_evidence(ai_detection, biometric=None, forensic=None):
    metrics = ai_detection["metrics"]
    probability = metrics.get("visual_ai_probability")
    synthetic_probability = metrics.get("synthetic_domain_probability")
    synthetic_threshold = metrics["thresholds"].get("high_synthetic_min_probability", 0.98)
    if synthetic_probability is not None and synthetic_probability >= synthetic_threshold:
        verdict, risk = "LIKELY_AI_GENERATED", "HIGH"
        confidence = round(min(synthetic_probability * 100, 99.9), 1)
        photo_text = "photo detector unavailable" if probability is None else f"photo detector estimates {probability:.2%} AI"
        explanation = (
            f"The domain model estimates {synthetic_probability:.2%} synthetic/rendered visual content; "
            f"{photo_text}. This estimate does not verify identity, liveness, or image provenance."
        )
    elif probability is None:
        verdict, risk, confidence = "UNCERTAIN", "MEDIUM", None
        explanation = "The trained detector is unavailable. No AI-or-real prediction was made."
    else:
        low = metrics["thresholds"]["likely_genuine_max_ai_probability"]
        high = metrics["thresholds"]["likely_ai_min_ai_probability"]
        confidence = round(max(probability, 1 - probability) * 100, 1)
        if probability >= high:
            verdict, risk = "LIKELY_AI_GENERATED", "HIGH"
        elif probability <= low:
            verdict, risk = "LIKELY_GENUINE", "LOW"
        else:
            verdict, risk = "UNCERTAIN", "MEDIUM"
        domain_text = "" if synthetic_probability is None else f" Domain model synthetic estimate: {synthetic_probability:.2%}."
        explanation = (f"The trained model estimates {probability:.2%} AI and {1-probability:.2%} real."
                       f"{domain_text} This estimate does not verify identity, liveness, or image provenance.")
    return {"status": "implemented", "verdict": verdict, "risk_level": risk,
            "confidence": confidence, "score": None if probability is None else probability * 100,
            "explanation": explanation, "warning_count": len(ai_detection["warnings"])}


def _apply_identity_upload_review(fusion, metadata, ai_detection):
    probability = ai_detection["metrics"].get("visual_ai_probability")
    strong_ai_evidence = probability is not None and probability >= AI_EVIDENCE_OVERRIDES_ID_REVIEW_MIN_PROBABILITY
    if metadata.get("identity_upload_context") and fusion["verdict"] == "LIKELY_GENUINE" and not strong_ai_evidence:
        return {**fusion, "verdict": "UNCERTAIN", "risk_level": "MEDIUM", "confidence": None,
                "explanation": (
                    fusion["explanation"]
                    + " This upload appears to be an ID, passport-size, or document photo, "
                    + "so it requires manual review instead of a positive genuine decision."
                )}
    return fusion


def _apply_camera_liveness_gate(fusion, liveness, ai_detection):
    metrics = ai_detection["metrics"]
    synthetic_probability = metrics.get("synthetic_domain_probability")
    synthetic_threshold = metrics["thresholds"].get("high_synthetic_min_probability", 0.98)
    if synthetic_probability is not None and synthetic_probability >= synthetic_threshold:
        return fusion
    if liveness.get("live_confirmed"):
        return {**fusion, "verdict": "LIKELY_GENUINE", "risk_level": "LOW",
                "confidence": liveness.get("live_probability") and round(float(liveness["live_probability"]) * 100, 1),
                "explanation": (
                    "Live presence was verified for this webcam capture. "
                    "The image-authenticity estimate is reported separately and should not be treated as identity proof."
                )}
    if liveness.get("prediction") == "POSSIBLE_PRESENTATION_ATTACK":
        explanation = "UNCERTAIN - possible photo or screen presentation. Live presence was not verified."
    else:
        explanation = "UNCERTAIN - live presence could not be verified."
    return {**fusion, "verdict": "UNCERTAIN", "risk_level": "MEDIUM", "confidence": None,
            "explanation": explanation}


def analyze_image(image_bytes: bytes, filename: str | None, source: str = "upload", live_frame_bytes=None) -> dict:
    image, metadata = decode_image(image_bytes)
    live_frame_bytes = live_frame_bytes or []
    live_images = []
    warnings = []
    dropped_live_frames = 0
    for frame_bytes in live_frame_bytes:
        try:
            frame_image, _ = decode_image(frame_bytes)
            live_images.append(frame_image)
        except ValueError:
            dropped_live_frames += 1
    metadata["filename"] = filename
    if dropped_live_frames:
        warnings.append(
            f"{dropped_live_frames} webcam frame(s) could not be decoded; liveness used the remaining frame(s)."
        )
    summary = {}
    model_deadline = time.monotonic() + IMAGE_MODEL_BUDGET_SECONDS
    try:
        if source == "upload":
            probability, summary = predict(image)
        else:
            visual_future = _analysis_executor.submit(predict, image)
            probability, summary = visual_future.result(timeout=_remaining_timeout(model_deadline, DETECTOR_TIMEOUT_SECONDS))
        status = "implemented"
    except concurrent.futures.TimeoutError:
        probability, status = None, "timeout"
        warnings.append("Trained detector timed out; no classification is available.")
    except Exception as exc:
        probability, status = None, "unavailable"
        import logging
        logging.getLogger(__name__).exception("Image detector failed")
        warnings.append("Trained detector could not run; no classification is available.")
    domain_future = _analysis_executor.submit(predict_synthetic_domain, image)
    try:
        synthetic_probability, domain_summary = domain_future.result(timeout=_remaining_timeout(model_deadline, DOMAIN_TIMEOUT_SECONDS))
        domain_status = "implemented"
    except concurrent.futures.TimeoutError:
        synthetic_probability, domain_summary, domain_status = None, {}, "timeout"
        warnings.append("Synthetic-domain detector timed out; the report used the local image model and forensics.")
    except Exception:
        synthetic_probability, domain_summary, domain_status = None, {}, "unavailable"
    counts = Counter(image_bytes)
    entropy = -sum((n / len(image_bytes)) * math.log2(n / len(image_bytes)) for n in counts.values())
    metadata["identity_upload_context"] = source == "upload" and _has_identity_upload_context(filename, metadata)
    thresholds = {**summary.get("thresholds", {}), **RUNTIME_REVIEW_THRESHOLDS}
    thresholds = {**thresholds, **domain_summary.get("thresholds", {"high_synthetic_min_probability": 0.98})}
    if min(image.size) < 128:
        warnings.append("Low resolution may reduce prediction reliability.")
    liveness = {"status": "NOT_ASSESSED", "live_probability": None}
    if source == "camera":
        from backend.services.liveness import analyze_liveness_sequence
        try:
            liveness = _run_with_timeout(analyze_liveness_sequence, LIVENESS_TIMEOUT_SECONDS, live_images or [image])
        except concurrent.futures.TimeoutError:
            liveness = {"status": "TIMEOUT", "prediction": "LIVE_NOT_CONFIRMED", "live_probability": None,
                        "live_confirmed": False, "message": "Live replay detection timed out; manual review is required.",
                        }
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Liveness analysis failed")
            liveness = {"status": "UNAVAILABLE", "prediction": "LIVE_NOT_CONFIRMED", "live_probability": None,
                        "live_confirmed": False,
                        "message": "Live presence could not be verified because the liveness check failed; manual review is required.",
                        }
        warnings.append(liveness.get("message", "Passive liveness estimate only."))
    metrics = {"visual_ai_probability": probability,
               "visual_real_probability": None if probability is None else 1 - probability,
               "visual_detector_status": status, "visual_detector_model_kind": "local_trained",
               "visual_detector_feature_model": summary.get("feature_model_key", "mobilenet_v3_small"),
               "visual_detector_model": LOCAL_DETECTOR_PATH.name,
               "synthetic_domain_probability": synthetic_probability,
               "synthetic_domain_status": domain_status,
               "synthetic_domain_model": domain_summary.get("model_id"),
               "entropy": round(entropy, 3),
               "bytes_per_pixel": round(len(image_bytes) / (image.width * image.height), 4),
               "source": source, "live_capture_score": int(source == "camera"), "thresholds": thresholds}
    ai = {"status": status, "score": None if probability is None else probability * 100,
          "warnings": warnings, "normal_signals": [], "metrics": metrics}
    fusion = fuse_evidence(ai)
    if source == "upload":
        fusion = _apply_identity_upload_review(fusion, metadata, ai)
    if source == "camera":
        fusion = _apply_camera_liveness_gate(fusion, liveness, ai)
    authenticity_fusion = fuse_evidence(ai)
    authenticity = {"verdict": authenticity_fusion["verdict"],
                    "confidence": authenticity_fusion["confidence"],
                    "ai_probability": probability,
                    "genuine_probability": metrics["visual_real_probability"],
                    "message": authenticity_fusion["explanation"]}
    if source == "camera":
        live_presence = {"verdict": "VERIFIED_LIVE" if liveness.get("live_confirmed") else "UNCERTAIN",
                         "confidence": None if liveness.get("live_probability") is None else round(float(liveness["live_probability"]) * 100, 1),
                         "message": liveness.get("message", "Live presence was not assessed."),
                         "prediction": liveness.get("prediction") or liveness.get("status")}
    else:
        live_presence = {"verdict": "NOT_ASSESSED", "confidence": None,
                         "message": "Live presence is only assessed for webcam capture.",
                         "prediction": "NOT_ASSESSED"}
    return {"filename": filename, "verdict": fusion["verdict"], "confidence": fusion["confidence"],
            "risk_level": fusion["risk_level"], "model_status": "READY" if probability is not None else "UNAVAILABLE",
            "ai_probability": probability, "genuine_probability": metrics["visual_real_probability"],
            "message": fusion["explanation"], "demo": False,
            "image_authenticity": authenticity,
            "live_presence": live_presence,
            "details": {"ai_generated_image_detection": ai, "evidence_fusion": fusion,
                        "facial_biometric_analysis": {"status": "not_implemented", "warnings": [],
                                                     "liveness_status": liveness["status"]},
                        "liveness": liveness,
                        "synthetic_domain_detection": {"status": domain_status,
                                                       "score": None if synthetic_probability is None else synthetic_probability * 100,
                                                       "model": domain_summary.get("model_id"),
                                                       "revision": domain_summary.get("revision"),
                                                       "thresholds": domain_summary.get("thresholds", {})},
                        "forensic_analysis": {"status": "implemented", "metadata": metadata, "warnings": []},
                        "model_evaluation": {"test": summary.get("test"), "test_rows": summary.get("test_rows"),
                                             "scope": summary.get("scope", "Face dataset only; camera replay not validated.")}}}


def save_feedback_image(image_bytes: bytes, filename: str | None, label: str) -> dict:
    label = label.strip().lower()
    if label not in {"real", "ai"}:
        raise ValueError("Feedback label must be 'real' or 'ai'.")
    _, metadata = decode_image(image_bytes)
    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[metadata["format"]]
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    opposite = FEEDBACK_DIR / ("ai" if label == "real" else "real")
    if list(opposite.glob(f"{digest}.*")):
        raise ValueError("This image already has the opposite label. Resolve the conflicting label before training.")
    folder = FEEDBACK_DIR / label
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{digest}.{extension}").write_bytes(image_bytes)
    return {"status": "saved", "label": label, "used_for_current_prediction": False}
