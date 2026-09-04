"""Placeholder for image metadata / EXIF inspection.

This does not parse real metadata.
"""


def extract_metadata(image_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "forensics.metadata",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Metadata extraction is not implemented. EXIF/header fields are not read.",
        "filename": filename,
        "bytes_received": len(image_bytes),
        "exif": None,
        "anomalies": None,
    }
