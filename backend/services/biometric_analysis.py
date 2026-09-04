from ml.face_analysis.detector import analyze_face


def analyze_biometrics(image_bytes: bytes, filename: str | None = None) -> dict:
    """Run facial/biometric analysis. Currently a demo placeholder."""
    return analyze_face(image_bytes, filename)
