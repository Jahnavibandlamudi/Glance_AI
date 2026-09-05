"""Passive presentation-attack estimate, separate from AI-image classification."""
import logging
import math
from functools import lru_cache
from pathlib import Path
from threading import Lock

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "antispoof"
_lock = Lock()


@lru_cache(maxsize=1)
def load_models():
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
        faces = faces[faces[:, 2] >= 0.6]
        if len(faces) != 1:
            return {"status": "NO_FACE" if not len(faces) else "MULTIPLE_FACES", "live_probability": None,
                    "message": "Exactly one clearly visible face is required for the replay check."}
        x1, y1, x2, y2 = faces[0, 3:7] * [width, height, width, height]
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(width - 1, int(x2)), min(height - 1, int(y2))
        if min(x2 - x1, y2 - y1) < 40:
            return {"status": "FACE_TOO_SMALL", "live_probability": None, "message": "Move closer to the camera."}
        # Upstream ToTensor uses BGR 0..255; upstream test.py maps class 1 to live.
        outputs = []
        with torch.inference_mode():
            for model, scale in models:
                crop = CropImage().crop(pixels, [x1, y1, x2-x1+1, y2-y1+1], scale, 80, 80)
                tensor = torch.from_numpy(crop.transpose(2, 0, 1).copy()).float().unsqueeze(0)
                outputs.append(torch.softmax(model(tensor), dim=1)[0].numpy())
        probabilities = np.mean(outputs, axis=0)
        live = float(probabilities[1])
        return {"status": "ASSESSED", "live_probability": live, "spoof_probability": 1-live,
                "prediction": "LIKELY_LIVE" if probabilities.argmax() == 1 else "POSSIBLE_REPLAY",
                "model": "MiniFASNetV2 + V1SE (upstream pretrained ensemble)",
                "face_box": [x1, y1, x2-x1+1, y2-y1+1],
                "message": "Passive single-frame estimate, not identity verification. Not validated on this camera."}
    except Exception:
        logging.getLogger(__name__).exception("Liveness detector failed")
        return {"status": "UNAVAILABLE", "live_probability": None,
                "message": "The trained replay detector could not run."}
