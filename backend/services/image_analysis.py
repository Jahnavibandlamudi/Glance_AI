from ml.image_detector.detector import detect_ai_generated_image
from services.biometric_analysis import analyze_biometrics
from services.forensic_analysis import analyze_forensics


def fuse_evidence(ai_detection: dict, biometric: dict, forensic: dict) -> dict:
    """Combine detector signals into a single verdict.

    This is a placeholder. It does not weight scores or produce a real decision.
    """
    return {
        "module": "services.image_analysis.fuse_evidence",
        "capability": "evidence_fusion",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Evidence fusion is not implemented. No real scores were combined.",
        "inputs_received": {
            "ai_generated_image_detection": ai_detection.get("status"),
            "facial_biometric_analysis": biometric.get("status"),
            "forensic_analysis": forensic.get("status"),
        },
        "verdict": "UNCERTAIN",
        "confidence": 50,
        "risk_level": "MEDIUM",
    }


def analyze_image(image_bytes: bytes, filename: str | None) -> dict:
    """Orchestrate image analysis. Public API fields stay demo-stable."""
    ai_detection = detect_ai_generated_image(image_bytes, filename)
    biometric = analyze_biometrics(image_bytes, filename)
    forensic = analyze_forensics(image_bytes, filename)
    fusion = fuse_evidence(ai_detection, biometric, forensic)

    return {
        "filename": filename,
        "verdict": fusion["verdict"],
        "confidence": fusion["confidence"],
        "risk_level": fusion["risk_level"],
        "message": "Image received successfully",
        "demo": True,
        "details": {
            "ai_generated_image_detection": ai_detection,
            "facial_biometric_analysis": biometric,
            "forensic_analysis": forensic,
            "evidence_fusion": fusion,
        },
    }
