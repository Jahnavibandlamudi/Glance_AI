def _placeholder_signal(name: str, filename: str | None, size_bytes: int) -> dict:
    return {
        "module": f"services.video_analysis.{name}",
        "status": "not_implemented",
        "demo": True,
        "filename": filename,
        "size_bytes": size_bytes,
        "message": "Video analysis is not implemented in this backend yet.",
    }


def fuse_video_evidence(
    deepfake_detection: dict,
    frame_analysis: dict,
    temporal_analysis: dict,
) -> dict:
    """Return an explicit non-decision until real video models are connected."""
    return {
        "module": "services.video_analysis.fuse_video_evidence",
        "demo": True,
        "status": "not_implemented",
        "message": "Video evidence fusion is not implemented. No real scores were combined.",
        "inputs_received": {
            "video_deepfake_detection": deepfake_detection.get("status"),
            "video_frame_analysis": frame_analysis.get("status"),
            "temporal_consistency_analysis": temporal_analysis.get("status"),
        },
        "verdict": "UNCERTAIN",
        "confidence": 0,
        "risk_level": "UNKNOWN",
    }


def analyze_video(video_bytes: bytes, filename: str | None) -> dict:
    """Keep the video endpoint import-safe until video analysis is implemented."""
    size_bytes = len(video_bytes)
    deepfake_detection = _placeholder_signal("detect_deepfake_video", filename, size_bytes)
    frame_analysis = _placeholder_signal("analyze_frames", filename, size_bytes)
    temporal_analysis = _placeholder_signal(
        "analyze_temporal_consistency",
        filename,
        size_bytes,
    )
    fusion = fuse_video_evidence(deepfake_detection, frame_analysis, temporal_analysis)

    return {
        "filename": filename,
        "verdict": fusion["verdict"],
        "confidence": fusion["confidence"],
        "risk_level": fusion["risk_level"],
        "message": "Video received, but video analysis is not implemented yet",
        "demo": True,
        "details": {
            "video_deepfake_detection": deepfake_detection,
            "video_frame_analysis": frame_analysis,
            "temporal_consistency_analysis": temporal_analysis,
            "evidence_fusion": fusion,
        },
    }
