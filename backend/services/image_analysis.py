"""Image classification with measured observations and no filename verdict overrides."""
import hashlib
import math
from collections import Counter
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

LOCAL_DETECTOR_PATH = Path(__file__).resolve().parents[1] / "models" / "visual_ai_detector.joblib"
FEEDBACK_DIR = Path(__file__).resolve().parents[1] / "data" / "feedback"
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


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


def fuse_evidence(ai_detection, biometric=None, forensic=None):
    metrics = ai_detection["metrics"]
    probability = metrics.get("visual_ai_probability")
    if probability is None:
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
        explanation = (f"The trained model estimates {probability:.1%} AI and {1-probability:.1%} real. "
                       "This estimate does not verify identity, liveness, or image provenance.")
    return {"status": "implemented", "verdict": verdict, "risk_level": risk,
            "confidence": confidence, "score": None if probability is None else probability * 100,
            "explanation": explanation, "warning_count": len(ai_detection["warnings"])}


def analyze_image(image_bytes: bytes, filename: str | None, source: str = "upload") -> dict:
    image, metadata = decode_image(image_bytes)
    metadata["filename"] = filename
    warnings = []
    summary = {}
    try:
        probability, summary = predict(image)
        status = "implemented"
    except Exception as exc:
        probability, status = None, "unavailable"
        import logging
        logging.getLogger(__name__).exception("Image detector failed")
        warnings.append("Trained detector could not run; no classification is available.")
    counts = Counter(image_bytes)
    entropy = -sum((n / len(image_bytes)) * math.log2(n / len(image_bytes)) for n in counts.values())
    thresholds = summary.get("thresholds", {"likely_genuine_max_ai_probability": 0.35,
                                          "likely_ai_min_ai_probability": 0.65})
    if min(image.size) < 128:
        warnings.append("Low resolution may reduce prediction reliability.")
    liveness = {"status": "NOT_ASSESSED", "live_probability": None}
    if source == "camera":
        from backend.services.liveness import analyze_liveness
        liveness = analyze_liveness(image)
        warnings.append(liveness.get("message", "Passive liveness estimate only."))
    metrics = {"visual_ai_probability": probability,
               "visual_real_probability": None if probability is None else 1 - probability,
               "visual_detector_status": status, "visual_detector_model_kind": "local_trained",
               "visual_detector_feature_model": summary.get("feature_model_key", "mobilenet_v3_small"),
               "visual_detector_model": LOCAL_DETECTOR_PATH.name,
               "entropy": round(entropy, 3),
               "bytes_per_pixel": round(len(image_bytes) / (image.width * image.height), 4),
               "source": source, "live_capture_score": int(source == "camera"), "thresholds": thresholds}
    ai = {"status": status, "score": None if probability is None else probability * 100,
          "warnings": warnings, "normal_signals": [], "metrics": metrics}
    fusion = fuse_evidence(ai)
    return {"filename": filename, "verdict": fusion["verdict"], "confidence": fusion["confidence"],
            "risk_level": fusion["risk_level"], "model_status": "READY" if probability is not None else "UNAVAILABLE",
            "ai_probability": probability, "genuine_probability": metrics["visual_real_probability"],
            "message": fusion["explanation"], "demo": False,
            "details": {"ai_generated_image_detection": ai, "evidence_fusion": fusion,
                        "facial_biometric_analysis": {"status": "not_implemented", "warnings": [],
                                                     "liveness_status": liveness["status"]},
                        "liveness": liveness,
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
