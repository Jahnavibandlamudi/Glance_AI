"""Placeholder for facial / biometric analysis.

No face detector, landmark model, or biometric model is loaded.
"""


def analyze_face(image_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "ml.face_analysis",
        "capability": "facial_biometric_analysis",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Facial/biometric analysis is not implemented. No ML model is loaded.",
        "filename": filename,
        "bytes_received": len(image_bytes),
        "faces_detected": None,
        "score": None,
        "label": None,
    }
