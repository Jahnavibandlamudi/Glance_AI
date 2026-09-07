"""Passive presentation-attack estimate, separate from AI-image classification."""
import logging
import math
from functools import lru_cache
from pathlib import Path
from threading import Lock
from backend.services.model_runtime import MODEL_LOAD_LOCK

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "antispoof"
_lock = Lock()
MIN_LIVE_CONFIRM_PROBABILITY = 0.65
HIGH_CONFIDENCE_LIVE_PROBABILITY = 0.88
MIN_SEQUENCE_FRAMES = 3
MIN_FRAME_MOTION = 0.003


@lru_cache(maxsize=1)
def load_models():
    with MODEL_LOAD_LOCK:
        import cv2
        import torch
        from backend.vendor.silent_face.MiniFASNet import MiniFASNetV2, MiniFASNetV1SE
        models = []
        for constructor, filename, scale in [(MiniFASNetV2, "2.7_80x80_MiniFASNetV2.pth", 2.7),
                                             (MiniFASNetV1SE, "4_0_0_80x80_MiniFASNetV1SE.pth", 4.0)]:
            model = constructor(conv6_kernel=(5, 5))
            state = torch.load(MODEL_DIR / filename, map_location="cpu", weights_only=True)
            model.load_state_dict({key.removeprefix("module."): value for key, value in state.items()})
            model.eval()
            models.append((model, scale))
        detector = cv2.dnn.readNetFromCaffe(str(MODEL_DIR / "deploy.prototxt"),
                                         str(MODEL_DIR / "Widerface-RetinaFace.caffemodel"))
        return detector, models


def analyze_liveness(image):
    try:
        import cv2
        import numpy as np
        import torch
        from backend.vendor.silent_face.generate_patches import CropImage
        detector, models = load_models()
        pixels = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        height, width = pixels.shape[:2]
        ratio = width / height
        small = cv2.resize(pixels, (max(1, int(192 * math.sqrt(ratio))), max(1, int(192 / math.sqrt(ratio)))))
        with _lock:
            detector.setInput(cv2.dnn.blobFromImage(small, 1, mean=(104, 117, 123)), "data")
            faces = detector.forward("detection_out").reshape(-1, 7)
        faces = faces[faces[:, 2] >= 0.42]
        if len(faces) != 1:
            return {"status": "NO_FACE" if not len(faces) else "MULTIPLE_FACES", "live_probability": None,
                    "live_confirmed": False,
                    "message": "Exactly one clearly visible face is required for the replay check."}
        x1, y1, x2, y2 = faces[0, 3:7] * [width, height, width, height]
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(width - 1, int(x2)), min(height - 1, int(y2))
        if min(x2 - x1, y2 - y1) < 28:
            return {"status": "FACE_TOO_SMALL", "live_probability": None, "live_confirmed": False,
                    "message": "Move closer to the camera."}
        # Upstream ToTensor uses BGR 0..255; upstream test.py maps class 1 to live.
        outputs = []
        with torch.inference_mode():
            for model, scale in models:
                crop = CropImage().crop(pixels, [x1, y1, x2-x1+1, y2-y1+1], scale, 80, 80)
                tensor = torch.from_numpy(crop.transpose(2, 0, 1).copy()).float().unsqueeze(0)
                outputs.append(torch.softmax(model(tensor), dim=1)[0].numpy())
        probabilities = np.mean(outputs, axis=0)
        live = float(probabilities[1])
        live_confirmed = bool(live >= MIN_LIVE_CONFIRM_PROBABILITY and probabilities.argmax() == 1)
        return {"status": "ASSESSED", "live_probability": live, "spoof_probability": 1-live,
                "prediction": "LIKELY_LIVE" if probabilities.argmax() == 1 else "POSSIBLE_REPLAY",
                "live_confirmed": live_confirmed,
                "confirm_live_min_probability": MIN_LIVE_CONFIRM_PROBABILITY,
                "model": "MiniFASNetV2 + V1SE (upstream pretrained ensemble)",
                "face_box": [x1, y1, x2-x1+1, y2-y1+1],
                "message": "Passive single-frame estimate, not identity verification. Not validated on this camera."}
    except Exception:
        logging.getLogger(__name__).exception("Liveness detector failed")
        return {"status": "UNAVAILABLE", "live_probability": None, "live_confirmed": False,
                "message": "The trained replay detector could not run."}


def _frame_motion(images):
    import cv2
    import numpy as np

    if len(images) < 2:
        return None
    grays = []
    for image in images:
        gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
        grays.append(cv2.resize(gray, (160, 120)))
    diffs = [
        float(np.mean(cv2.absdiff(grays[index - 1], grays[index])))
        for index in range(1, len(grays))
    ]
    return round(sum(diffs) / len(diffs), 3)


def analyze_liveness_sequence(images):
    if not images:
        return {"status": "NOT_ASSESSED", "live_probability": None, "live_confirmed": False,
                "message": "No live-capture frames were provided."}
    if len(images) > MIN_SEQUENCE_FRAMES:
        images = [images[0], images[len(images) // 2], images[-1]]
    single_results = [analyze_liveness(image) for image in images]
    assessed = [result for result in single_results if result.get("live_probability") is not None]
    motion = None
    try:
        motion = _frame_motion(images)
    except Exception:
        logging.getLogger(__name__).exception("Frame motion analysis failed")
    if not assessed:
        first = single_results[0]
        return {**first, "frame_count": len(images), "frame_motion": motion, "live_confirmed": False,
                "message": first.get("message", "Live presence could not be assessed.")}
    live_values = sorted(float(result["live_probability"]) for result in assessed)
    median_live = live_values[len(live_values) // 2]
    spoof = 1 - median_live
    enough_frames = len(images) >= MIN_SEQUENCE_FRAMES
    enough_motion = motion is not None and motion >= MIN_FRAME_MOTION
    required_assessed = min(len(images), max(2, round(len(images) * 0.67)))
    enough_faces_assessed = len(assessed) >= required_assessed
    live_votes = sum(result.get("prediction") == "LIKELY_LIVE" for result in assessed)
    majority_live = live_votes >= max(1, math.ceil(len(assessed) / 2))
    high_confidence_live = (
        enough_faces_assessed
        and majority_live
        and median_live >= HIGH_CONFIDENCE_LIVE_PROBABILITY
    )
    live_confirmed = (
        enough_frames
        and enough_faces_assessed
        and majority_live
        and median_live >= MIN_LIVE_CONFIRM_PROBABILITY
        and (enough_motion or high_confidence_live)
    )
    if live_confirmed:
        prediction = "LIKELY_LIVE"
        if enough_motion:
            message = "Live presence was supported by the anti-spoof model and frame-to-frame camera motion."
        else:
            message = "Live presence was supported by high anti-spoof confidence across the capture sequence."
    else:
        if enough_faces_assessed and majority_live and not enough_motion:
            prediction = "POSSIBLE_PRESENTATION_ATTACK"
            message = "Live presence is uncertain: possible photo or screen presentation."
        else:
            prediction = "LIVE_NOT_CONFIRMED"
            message = "Live presence is uncertain: live presence could not be verified."
        missing = []
        if median_live < MIN_LIVE_CONFIRM_PROBABILITY:
            missing.append("anti-spoof confidence is below the live threshold")
        if not enough_frames:
            missing.append("too few camera frames were submitted")
        if not enough_motion:
            missing.append("not enough natural frame-to-frame motion was measured")
        if not enough_faces_assessed:
            missing.append("too few frames had one clearly visible face")
        if missing:
            message += " " + "; ".join(missing) + "."
    return {"status": "ASSESSED", "live_probability": median_live, "spoof_probability": spoof,
            "prediction": prediction, "live_confirmed": live_confirmed,
            "frame_count": len(images), "assessed_frame_count": len(assessed),
            "required_assessed_frame_count": required_assessed,
            "frame_motion": motion, "min_frame_motion": MIN_FRAME_MOTION,
            "confirm_live_min_probability": MIN_LIVE_CONFIRM_PROBABILITY,
            "high_confidence_live_min_probability": HIGH_CONFIDENCE_LIVE_PROBABILITY,
            "per_frame_predictions": [result.get("prediction") or result.get("status") for result in single_results],
            "model": "MiniFASNetV2 + V1SE (upstream pretrained ensemble)",
            "message": message}
