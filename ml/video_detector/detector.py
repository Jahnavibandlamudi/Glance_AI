"""Placeholder for video deepfake, frame, and temporal analysis.

No video model is loaded. These functions do not decode or score frames.
"""


def detect_deepfake_video(video_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "ml.video_detector",
        "capability": "video_deepfake_detection",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Video deepfake detection is not implemented. No ML model is loaded.",
        "filename": filename,
        "bytes_received": len(video_bytes),
        "score": None,
        "label": None,
    }


def analyze_frames(video_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "ml.video_detector",
        "capability": "video_frame_analysis",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Video frame analysis is not implemented. Frames are not extracted or scored.",
        "filename": filename,
        "bytes_received": len(video_bytes),
        "frame_count": None,
        "score": None,
        "label": None,
    }


def analyze_temporal_consistency(video_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "ml.video_detector",
        "capability": "temporal_consistency_analysis",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Temporal consistency analysis is not implemented. No temporal model is loaded.",
        "filename": filename,
        "bytes_received": len(video_bytes),
        "score": None,
        "label": None,
    }
