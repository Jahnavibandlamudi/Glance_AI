from forensics.compression import analyze_compression
from forensics.ela import error_level_analysis
from forensics.metadata import extract_metadata
from forensics.texture import analyze_texture


def analyze_forensics(image_bytes: bytes, filename: str | None = None) -> dict:
    """Collect image forensic signals. Currently demo placeholders only."""
    return {
        "module": "services.forensic_analysis",
        "demo": True,
        "status": "placeholder",
        "message": "DEMO: Forensic analysis is not implemented. Submodules did not inspect the file.",
        "metadata": extract_metadata(image_bytes, filename),
        "ela": error_level_analysis(image_bytes, filename),
        "texture": analyze_texture(image_bytes, filename),
        "compression": analyze_compression(image_bytes, filename),
    }
