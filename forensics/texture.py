"""Placeholder for texture / noise-pattern analysis.

This does not compute texture or PRNU features.
"""


def analyze_texture(image_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "forensics.texture",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Texture analysis is not implemented. No texture or noise features are computed.",
        "filename": filename,
        "bytes_received": len(image_bytes),
        "score": None,
        "features": None,
    }
