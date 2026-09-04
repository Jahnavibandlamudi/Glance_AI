"""Placeholder for Error Level Analysis (ELA).

This does not recompress the image or compute an ELA map.
"""


def error_level_analysis(image_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "forensics.ela",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Error Level Analysis is not implemented. No ELA map is computed.",
        "filename": filename,
        "bytes_received": len(image_bytes),
        "score": None,
        "ela_map": None,
    }
