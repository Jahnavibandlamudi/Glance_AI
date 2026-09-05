import math
import os
import statistics
import struct
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re


SUPPORTED_FORMATS = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
}

VISUAL_DETECTOR_PATH = (
    Path(__file__).resolve().parents[1] / "models" / "visual_ai_detector.joblib"
)


@dataclass(frozen=True)
class ImageMetadata:
    filename: str | None
    extension: str | None
    format: str | None
    width: int | None
    height: int | None
    size_bytes: int
    has_exif: bool
    has_png_text: bool


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, round(value)))


def _extension(filename: str | None) -> str | None:
    if not filename:
        return None
    suffix = os.path.splitext(filename)[1].lower().lstrip(".")
    return suffix or None


def _detect_format(image_bytes: bytes) -> str | None:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "WEBP"
    return None


def _jpeg_dimensions(image_bytes: bytes) -> tuple[int | None, int | None]:
    index = 2
    while index + 9 < len(image_bytes):
        if image_bytes[index] != 0xFF:
            index += 1
            continue

        marker = image_bytes[index + 1]
        index += 2

        while marker == 0xFF and index < len(image_bytes):
            marker = image_bytes[index]
            index += 1

        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue

        if index + 2 > len(image_bytes):
            break

        segment_length = struct.unpack(">H", image_bytes[index : index + 2])[0]
        if segment_length < 2 or index + segment_length > len(image_bytes):
            break

        is_start_of_frame = marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }
        if is_start_of_frame and segment_length >= 7:
            height = struct.unpack(">H", image_bytes[index + 3 : index + 5])[0]
            width = struct.unpack(">H", image_bytes[index + 5 : index + 7])[0]
            return width, height

        index += segment_length

    return None, None


def _png_dimensions(image_bytes: bytes) -> tuple[int | None, int | None]:
    if len(image_bytes) < 24:
        return None, None
    width, height = struct.unpack(">II", image_bytes[16:24])
    return width, height


def _webp_dimensions(image_bytes: bytes) -> tuple[int | None, int | None]:
    if len(image_bytes) < 30:
        return None, None

    chunk_type = image_bytes[12:16]
    if chunk_type == b"VP8X" and len(image_bytes) >= 30:
        width = int.from_bytes(image_bytes[24:27], "little") + 1
        height = int.from_bytes(image_bytes[27:30], "little") + 1
        return width, height

    if chunk_type == b"VP8 " and len(image_bytes) >= 30:
        width = struct.unpack("<H", image_bytes[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", image_bytes[28:30])[0] & 0x3FFF
        return width, height

    if chunk_type == b"VP8L" and len(image_bytes) >= 25:
        bits = int.from_bytes(image_bytes[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height

    return None, None


def _dimensions(image_bytes: bytes, image_format: str | None) -> tuple[int | None, int | None]:
    if image_format == "JPEG":
        return _jpeg_dimensions(image_bytes)
    if image_format == "PNG":
        return _png_dimensions(image_bytes)
    if image_format == "WEBP":
        return _webp_dimensions(image_bytes)
    return None, None


def _has_exif(image_bytes: bytes) -> bool:
    return b"Exif\x00\x00" in image_bytes[:65536]


def _has_png_text(image_bytes: bytes) -> bool:
    return any(chunk in image_bytes for chunk in (b"tEXt", b"iTXt", b"zTXt"))


def _metadata(image_bytes: bytes, filename: str | None) -> ImageMetadata:
    image_format = _detect_format(image_bytes)
    width, height = _dimensions(image_bytes, image_format)
    return ImageMetadata(
        filename=filename,
        extension=_extension(filename),
        format=image_format,
        width=width,
        height=height,
        size_bytes=len(image_bytes),
        has_exif=_has_exif(image_bytes),
        has_png_text=_has_png_text(image_bytes),
    )


def _entropy(image_bytes: bytes) -> float:
    if not image_bytes:
        return 0.0

    counts = Counter(image_bytes)
    size = len(image_bytes)
    return -sum((count / size) * math.log2(count / size) for count in counts.values())


def _repetition_score(image_bytes: bytes) -> float:
    if len(image_bytes) < 4096:
        return 0.0

    sample = image_bytes[: min(len(image_bytes), 262144)]
    chunk_size = 64
    chunks = [
        sample[index : index + chunk_size]
        for index in range(0, len(sample) - chunk_size + 1, chunk_size)
    ]
    if not chunks:
        return 0.0

    repeated = len(chunks) - len(set(chunks))
    return repeated / len(chunks)


def _byte_smoothness_score(image_bytes: bytes) -> float:
    if len(image_bytes) < 4096:
        return 0.0

    sample = image_bytes[: min(len(image_bytes), 131072)]
    windows = [sample[index : index + 512] for index in range(0, len(sample) - 512, 512)]
    if len(windows) < 4:
        return 0.0

    deviations = [statistics.pstdev(window) for window in windows]
    if not deviations:
        return 0.0

    mean_deviation = statistics.mean(deviations)
    return _clamp((38 - mean_deviation) * 3) / 100


def _filename_prompt_score(filename: str | None) -> float:
    if not filename:
        return 0.0

    lowered = filename.lower()
    prompt_terms = (
        "midjourney",
        "stable-diffusion",
        "stablediffusion",
        "dalle",
        "dall-e",
        "ai-generated",
        "generated",
        "synthetic",
        "text2img",
        "txt2img",
        "deepfake",
        "face-swap",
        "faceswap",
    )
    if any(term in lowered for term in prompt_terms):
        return 1.0

    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    return 1.0 if tokens.intersection({"ai", "fake", "synthetic"}) else 0.0


def _embedded_generator_score(image_bytes: bytes) -> float:
    sample = image_bytes[: min(len(image_bytes), 524288)].lower()
    generator_terms = (
        b"prompt",
        b"negative prompt",
        b"seed",
        b"sampler",
        b"cfg scale",
        b"steps",
        b"stable diffusion",
        b"stablediffusion",
        b"midjourney",
        b"comfyui",
        b"automatic1111",
        b"novelai",
        b"dall-e",
        b"dalle",
        b"adobe firefly",
    )
    matches = sum(1 for term in generator_terms if term in sample)
    return min(matches / 3, 1.0)


def _megapixels(metadata: ImageMetadata) -> float | None:
    if metadata.width is None or metadata.height is None:
        return None
    return (metadata.width * metadata.height) / 1_000_000


def _bytes_per_pixel(metadata: ImageMetadata) -> float | None:
    if not metadata.width or not metadata.height:
        return None
    return metadata.size_bytes / (metadata.width * metadata.height)


def _has_embedded_provenance(metadata: ImageMetadata) -> bool:
    return metadata.has_exif or metadata.has_png_text


def _identity_photo_filename_score(filename: str | None) -> float:
    if not filename:
        return 0.0

    tokens = set(re.findall(r"[a-z0-9]+", filename.lower()))
    identity_terms = {
        "passport",
        "id",
        "kyc",
        "visa",
        "headshot",
        "portrait",
        "profile",
        "photo",
        "pic",
    }
    return 1.0 if tokens.intersection(identity_terms) else 0.0


def _passport_style_score(metadata: ImageMetadata, image_bytes: bytes) -> float:
    if not metadata.width or not metadata.height:
        return 0.0

    aspect_ratio = metadata.width / metadata.height
    passport_aspect = 0.58 <= aspect_ratio <= 0.92
    if not passport_aspect:
        return 0.0

    try:
        import numpy as np
        from PIL import Image

        image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((96, 128))
        pixels = np.asarray(image, dtype=np.float32) / 255.0
    except Exception:
        return 0.0

    border = np.concatenate(
        [
            pixels[:12, :, :].reshape(-1, 3),
            pixels[-12:, :, :].reshape(-1, 3),
            pixels[:, :12, :].reshape(-1, 3),
            pixels[:, -12:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    center = pixels[32:96, 24:72, :].reshape(-1, 3)
    border_uniformity = 1.0 - min(float(border.std()) / 0.28, 1.0)
    center_contrast = min(float(abs(center.mean() - border.mean())) / 0.28, 1.0)
    size_score = 1.0 if min(metadata.width, metadata.height) >= 180 else 0.5
    return round((border_uniformity * 0.55) + (center_contrast * 0.25) + (size_score * 0.2), 3)


@lru_cache(maxsize=1)
def _load_visual_detector():
    if not VISUAL_DETECTOR_PATH.exists():
        return None, "No trained visual detector artifact found."

    try:
        import joblib
        import torch
        from PIL import Image
        from torchvision import models
    except Exception as exc:
        return None, f"Visual detector dependencies are unavailable: {exc}"

    try:
        artifact = joblib.load(VISUAL_DETECTOR_PATH)
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        model = models.mobilenet_v3_small(weights=weights)
        model.classifier = torch.nn.Identity()
        model.eval()
        return (artifact, torch, Image, model, weights.transforms()), None
    except Exception as exc:
        return None, f"Visual detector could not be loaded: {exc}"


def _predict_visual_ai_probability(image_bytes: bytes) -> dict:
    runtime, error = _load_visual_detector()
    if error:
        return {"status": "unavailable", "error": error}

    artifact, torch, Image, model, transform = runtime
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return {"status": "unavailable", "error": f"Image could not be decoded: {exc}"}

    with torch.no_grad():
        tensor = transform(image).unsqueeze(0)
        features = model(tensor).detach().cpu().numpy()

    classifier = artifact["classifier"]
    ai_probability = float(classifier.predict_proba(features)[0][1])
    return {
        "status": "implemented",
        "ai_probability": ai_probability,
        "real_probability": 1.0 - ai_probability,
        "artifact": str(VISUAL_DETECTOR_PATH),
        "training_summary": artifact.get("training_summary", {}),
    }


def _analyze_ai_generation(metadata: ImageMetadata, image_bytes: bytes) -> dict:
    entropy = _entropy(image_bytes)
    repeated_chunks = _repetition_score(image_bytes)
    smoothness = _byte_smoothness_score(image_bytes)
    bytes_per_pixel = _bytes_per_pixel(metadata)
    filename_prompt = _filename_prompt_score(metadata.filename)
    identity_filename = _identity_photo_filename_score(metadata.filename)
    embedded_generator = _embedded_generator_score(image_bytes)
    passport_style = _passport_style_score(metadata, image_bytes)
    visual_prediction = _predict_visual_ai_probability(image_bytes)

    warnings = []
    normal_signals = []
    score = 8

    if metadata.format is None:
        warnings.append("File signature is not a supported image format")
        score += 35
    else:
        normal_signals.append(f"Valid {metadata.format} image signature")

    if metadata.extension and metadata.extension in SUPPORTED_FORMATS:
        expected = SUPPORTED_FORMATS[metadata.extension]
        if metadata.format and expected != metadata.format:
            warnings.append("Filename extension does not match the image bytes")
            score += 24
        else:
            normal_signals.append("Filename extension matches the image bytes")

    if metadata.width and metadata.height:
        normal_signals.append(f"Readable dimensions: {metadata.width}x{metadata.height}")
        if metadata.width < 128 or metadata.height < 128:
            warnings.append("Image is too small for reliable identity analysis")
            score += 10
    else:
        warnings.append("Image dimensions could not be read")
        score += 22

    if metadata.has_exif:
        normal_signals.append("Camera/editor EXIF metadata is present")
        score -= 14
    elif metadata.format == "JPEG":
        warnings.append("JPEG has no EXIF metadata")
        score += 18

    if metadata.has_png_text:
        normal_signals.append("PNG metadata text chunk is present")
    elif metadata.format in {"PNG", "WEBP"}:
        warnings.append("Image has limited embedded provenance metadata")
        score += 16

    if entropy < 4.5:
        warnings.append("Very low byte entropy")
        score += 18
    elif entropy > 7.9:
        warnings.append("Extremely high byte entropy")
        score += 6
    else:
        normal_signals.append("Byte entropy is within a normal compressed-image range")

    if repeated_chunks > 0.12:
        warnings.append("Repeated byte patterns are higher than expected")
        score += repeated_chunks * 80
    else:
        normal_signals.append("No strong repeated byte pattern detected")

    if smoothness > 0.25:
        warnings.append("Compression texture appears unusually smooth")
        score += smoothness * 30

    if bytes_per_pixel is not None:
        if bytes_per_pixel < 0.05:
            warnings.append("File is unusually small for its dimensions")
            score += 12
        elif bytes_per_pixel > 8:
            warnings.append("File is unusually large for its dimensions")
            score += 6
        else:
            normal_signals.append("File size is plausible for the image dimensions")

    if filename_prompt:
        warnings.append("Filename contains common generated-image terms")
        score += 34

    if embedded_generator:
        warnings.append("Embedded metadata contains generator-style terms")
        score += 38 * embedded_generator

    heuristic_score = _clamp(score)
    if visual_prediction["status"] == "implemented":
        visual_score = _clamp(visual_prediction["ai_probability"] * 100)
        has_generator_evidence = bool(filename_prompt or embedded_generator)
        has_identity_photo_safeguard = (
            (passport_style >= 0.7 or identity_filename)
            and not has_generator_evidence
        )
        if visual_score >= 90 and has_identity_photo_safeguard:
            score = 74
            warnings.append(
                "Formal identity photo can resemble generated imagery; manual review is required"
            )
        elif visual_score >= 99:
            score = max(visual_score, heuristic_score)
            warnings.append("Visual detector found very strong AI-generation patterns")
        elif visual_score >= 65:
            score = max(visual_score, heuristic_score)
            warnings.append("Visual detector found AI-generation patterns")
        elif visual_score <= 35:
            if has_generator_evidence:
                score = max(visual_score, 72)
                warnings.append("Visual detector disagrees with explicit generator indicators")
            else:
                score = visual_score
                normal_signals.append("Visual detector found genuine-image patterns")
        else:
            score = visual_score
            warnings.append("Visual detector result is borderline")
    else:
        score = heuristic_score
        normal_signals.append(visual_prediction["error"])

    score = _clamp(score)

    return {
        "module": "services.image_analysis.detect_ai_generated_image",
        "status": "implemented",
        "score": score,
        "confidence": score,
        "warnings": warnings,
        "normal_signals": normal_signals,
        "metrics": {
            "entropy": round(entropy, 3),
            "repeated_chunk_ratio": round(repeated_chunks, 4),
            "smoothness_score": round(smoothness, 3),
            "bytes_per_pixel": round(bytes_per_pixel, 4) if bytes_per_pixel is not None else None,
            "embedded_generator_score": round(embedded_generator, 3),
            "identity_photo_filename_score": identity_filename,
            "passport_style_score": passport_style,
            "identity_photo_safeguard": (
                bool((passport_style >= 0.7 or identity_filename) and not (filename_prompt or embedded_generator))
                if visual_prediction["status"] == "implemented"
                else False
            ),
            "heuristic_score": heuristic_score,
            "visual_ai_probability": (
                round(visual_prediction["ai_probability"], 4)
                if visual_prediction["status"] == "implemented"
                else None
            ),
            "visual_real_probability": (
                round(visual_prediction["real_probability"], 4)
                if visual_prediction["status"] == "implemented"
                else None
            ),
            "visual_detector_status": visual_prediction["status"],
            "embedded_provenance_present": _has_embedded_provenance(metadata),
            "megapixels": round(_megapixels(metadata), 3) if _megapixels(metadata) is not None else None,
        },
    }


def _analyze_biometrics(metadata: ImageMetadata) -> dict:
    warnings = []
    normal_signals = []

    if metadata.width is None or metadata.height is None:
        warnings.append("Cannot assess face suitability without image dimensions")
        status = "needs_review"
    elif metadata.width < 256 or metadata.height < 256:
        warnings.append("Image resolution is low for biometric checks")
        status = "needs_review"
    else:
        normal_signals.append("Resolution is sufficient for downstream face checks")
        status = "passed"

    return {
        "module": "services.image_analysis.analyze_biometrics",
        "status": status,
        "warnings": warnings,
        "normal_signals": normal_signals,
        "note": "Face landmark verification is not available in this lightweight backend yet.",
    }


def _analyze_forensics(metadata: ImageMetadata) -> dict:
    warnings = []
    normal_signals = []

    if metadata.format in {"JPEG", "PNG", "WEBP"}:
        normal_signals.append("Image container is supported")
    else:
        warnings.append("Unsupported or unreadable image container")

    if metadata.size_bytes < 1024:
        warnings.append("Image file is extremely small")
    else:
        normal_signals.append("Image file has enough data for basic checks")

    return {
        "module": "services.image_analysis.analyze_forensics",
        "status": "implemented",
        "warnings": warnings,
        "normal_signals": normal_signals,
        "metadata": {
            "filename": metadata.filename,
            "extension": metadata.extension,
            "format": metadata.format,
            "width": metadata.width,
            "height": metadata.height,
            "size_bytes": metadata.size_bytes,
            "has_exif": metadata.has_exif,
            "has_png_text": metadata.has_png_text,
        },
    }


def fuse_evidence(ai_detection: dict, biometric: dict, forensic: dict) -> dict:
    """Combine backend signals conservatively to avoid false AI positives."""
    score = ai_detection["score"]
    warning_count = (
        len(ai_detection.get("warnings", []))
        + len(biometric.get("warnings", []))
        + len(forensic.get("warnings", []))
    )

    visual_status = ai_detection.get("metrics", {}).get("visual_detector_status")
    provenance_present = ai_detection.get("metrics", {}).get("embedded_provenance_present")
    identity_photo_safeguard = ai_detection.get("metrics", {}).get("identity_photo_safeguard")

    if visual_status == "implemented" and score >= 99 and not identity_photo_safeguard:
        verdict = "LIKELY_AI_GENERATED"
        risk_level = "HIGH"
        confidence = 92
        explanation = "Visual detector found very strong AI-generation patterns."
    elif visual_status == "implemented" and score >= 65 and not identity_photo_safeguard:
        verdict = "LIKELY_AI_GENERATED"
        risk_level = "HIGH"
        confidence = _clamp(min(92, score))
        explanation = "Visual detector found AI-generation patterns; metadata and forensic signals are supporting evidence."
    elif visual_status == "implemented" and score <= 40:
        verdict = "LIKELY_GENUINE"
        risk_level = "LOW"
        confidence = _clamp(min(88, 100 - score))
        if provenance_present:
            explanation = "Visual detector found genuine-image patterns and embedded provenance is present."
        else:
            explanation = "Visual detector found genuine-image patterns, but confidence is capped because embedded provenance is missing."
    elif visual_status == "implemented":
        verdict = "UNCERTAIN"
        risk_level = "MEDIUM"
        confidence = _clamp(max(score, 100 - score))
        explanation = "Visual detector result is borderline, so this image should be manually reviewed."
    elif score >= 70 and warning_count >= 3:
        verdict = "LIKELY_AI_GENERATED"
        risk_level = "HIGH"
        confidence = _clamp(score)
        explanation = (
            "Conservative fusion only flags AI-generated when multiple independent "
            "signals are suspicious."
        )
    elif score >= 30 and warning_count >= 2:
        verdict = "UNCERTAIN"
        risk_level = "MEDIUM"
        confidence = _clamp(score)
        explanation = (
            "Conservative fusion only flags AI-generated when multiple independent "
            "signals are suspicious."
        )
    else:
        verdict = "LIKELY_GENUINE"
        risk_level = "LOW"
        confidence = _clamp(100 - min(score, 55))
        explanation = (
            "Conservative fusion only flags AI-generated when multiple independent "
            "signals are suspicious."
        )

    return {
        "module": "services.image_analysis.fuse_evidence",
        "status": "implemented",
        "verdict": verdict,
        "confidence": confidence,
        "risk_level": risk_level,
        "score": score,
        "warning_count": warning_count,
        "explanation": explanation,
    }


def analyze_image(image_bytes: bytes, filename: str | None) -> dict:
    """Orchestrate image analysis for uploaded KYC images."""
    metadata = _metadata(image_bytes, filename)
    ai_detection = _analyze_ai_generation(metadata, image_bytes)
    biometric = _analyze_biometrics(metadata)
    forensic = _analyze_forensics(metadata)
    fusion = fuse_evidence(ai_detection, biometric, forensic)

    return {
        "filename": filename,
        "verdict": fusion["verdict"],
        "confidence": fusion["confidence"],
        "risk_level": fusion["risk_level"],
        "message": "Image received and analyzed successfully",
        "demo": False,
        "details": {
            "ai_generated_image_detection": ai_detection,
            "facial_biometric_analysis": biometric,
            "forensic_analysis": forensic,
            "evidence_fusion": fusion,
        },
    }
