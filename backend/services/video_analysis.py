from ml.video_detector.detector import (
    analyze_frames,
    analyze_temporal_consistency,
    detect_deepfake_video,
)


def fuse_video_evidence(
    deepfake_detection: dict,
    frame_analysis: dict,
    temporal_analysis: dict,
) -> dict:
    """Combine video signals into a single verdict.

    This is a placeholder. It does not weight scores or produce a real decision.
    """
    return {
        "module": "services.video_analysis.fuse_video_evidence",
        "capability": "evidence_fusion",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Video evidence fusion is not implemented. No real scores were combined.",
        "inputs_received": {
            "video_deepfake_detection": deepfake_detection.get("status"),
            "video_frame_analysis": frame_analysis.get("status"),
            "temporal_consistency_analysis": temporal_analysis.get("status"),
        },
        "verdict": "UNCERTAIN",
        "confidence": 50,
        "risk_level": "MEDIUM",
    }


def analyze_video(video_bytes: bytes, filename: str | None) -> dict:
    """Orchestrate video analysis. Public API fields stay demo-stable."""
    deepfake_detection = detect_deepfake_video(video_bytes, filename)
    frame_analysis = analyze_frames(video_bytes, filename)
    temporal_analysis = analyze_temporal_consistency(video_bytes, filename)
    fusion = fuse_video_evidence(deepfake_detection, frame_analysis, temporal_analysis)

    return {
        "filename": filename,
        "verdict": fusion["verdict"],
        "confidence": fusion["confidence"],
        "risk_level": fusion["risk_level"],
        "message": "Video received successfully",
        "demo": True,
        "details": {
            "video_deepfake_detection": deepfake_detection,
            "video_frame_analysis": frame_analysis,
            "temporal_consistency_analysis": temporal_analysis,
            "evidence_fusion": fusion,
        },
    }
