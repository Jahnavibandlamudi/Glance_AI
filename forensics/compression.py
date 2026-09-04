"""Placeholder for compression-artifact analysis.

This does not inspect JPEG quantization tables or recompression traces.
"""


def analyze_compression(image_bytes: bytes, filename: str | None = None) -> dict:
    return {
        "module": "forensics.compression",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Compression analysis is not implemented. No compression artifacts are measured.",
        "filename": filename,
        "bytes_received": len(image_bytes),
        "score": None,
        "artifacts": None,
    }
