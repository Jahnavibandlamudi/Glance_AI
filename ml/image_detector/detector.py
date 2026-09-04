"""Placeholder for AI-generated image detection.

No model is loaded. Return values are demo-only and must not be treated
as real detector scores.
"""


def detect_ai_generated_image(image_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "ml.image_detector",
        "capability": "ai_generated_image_detection",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: AI-generated image detection is not implemented. No ML model is loaded.",
        "filename": filename,
        "bytes_received": len(image_bytes),
        "score": None,
        "label": None,
    }
