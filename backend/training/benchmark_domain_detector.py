"""Benchmark a local zero-shot visual domain detector."""
import json
import time
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from PIL import Image, ImageOps
from sklearn.metrics import accuracy_score, confusion_matrix
from transformers import AutoModel, AutoProcessor

MODEL_ID = "google/siglip-base-patch16-224"
REVISION = "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed"
DESTINATION = Path("backend/models/siglip_domain")
REPORT = Path("backend/models/domain_benchmark.json")

PHOTO_PROMPTS = [
    "a real camera photograph of a person",
    "a real smartphone photo of a human",
    "a passport photo or identity photo captured by a camera",
]

SYNTHETIC_PROMPTS = [
    "a synthetic AI generated illustration of a person",
    "a 3D cartoon render of a person",
    "a computer generated portrait, not a real camera photo",
]


def main():
    torch.set_num_threads(4)
    snapshot_download(
        MODEL_ID,
        revision=REVISION,
        local_dir=DESTINATION,
        allow_patterns=[
            "config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "special_tokens_map.json",
            "spiece.model",
            "tokenizer.json",
            "tokenizer_config.json",
        ],
    )
    processor = AutoProcessor.from_pretrained(DESTINATION, local_files_only=True)
    model = AutoModel.from_pretrained(
        DESTINATION,
        local_files_only=True,
        use_safetensors=True,
        trust_remote_code=False,
    ).eval()
    prompts = PHOTO_PROMPTS + SYNTHETIC_PROMPTS
    text_inputs = processor(text=prompts, padding="max_length", return_tensors="pt")
    rows = [(Path(r"C:\Users\bnsja\OneDrive\Documents\AI image.webp"), 1, "user_example")]
    for label, folder in [(0, "real"), (1, "ai")]:
        rows += [(p, label, "feedback") for p in Path("backend/data/feedback", folder).glob("*")]
    root = Path("backend/data/raw/140k/real_vs_fake/real-vs-fake/test")
    for label, folder in enumerate(("real", "fake")):
        rows += [(p, label, "face_test") for p in sorted((root / folder).glob("*.jpg"))[:100]]
    results = []
    with torch.inference_mode():
        for start in range(0, len(rows), 8):
            batch = rows[start:start + 8]
            images = []
            for path, _, _ in batch:
                with Image.open(path) as image:
                    images.append(ImageOps.exif_transpose(image).convert("RGB"))
            image_inputs = processor(images=images, return_tensors="pt")
            then = time.perf_counter()
            outputs = model(**image_inputs, **text_inputs)
            scores = outputs.logits_per_image.softmax(dim=1)
            photo_score = scores[:, :len(PHOTO_PROMPTS)].sum(dim=1)
            synthetic_score = scores[:, len(PHOTO_PROMPTS):].sum(dim=1)
            synthetic_probability = (synthetic_score / (photo_score + synthetic_score)).tolist()
            for (path, label, group), probability in zip(batch, synthetic_probability):
                result = {
                    "filename": path.name,
                    "label": label,
                    "group": group,
                    "synthetic_probability": float(probability),
                }
                results.append(result)
                if group != "face_test":
                    print(result, flush=True)
            print(f"Completed {min(start + 8, len(rows))}/{len(rows)} ({time.perf_counter() - then:.2f}s/batch)", flush=True)
    subset = [row for row in results if row["group"] == "face_test"]
    truth = [row["label"] for row in subset]
    predicted = [int(row["synthetic_probability"] >= 0.5) for row in subset]
    report = {
        "model_id": MODEL_ID,
        "revision": REVISION,
        "photo_prompts": PHOTO_PROMPTS,
        "synthetic_prompts": SYNTHETIC_PROMPTS,
        "rows": results,
        "face_test_accuracy": accuracy_score(truth, predicted),
        "face_test_confusion": confusion_matrix(truth, predicted).tolist(),
    }
    REPORT.write_text(json.dumps(report, indent=2))
    print({key: value for key, value in report.items() if key != "rows"}, flush=True)


if __name__ == "__main__":
    main()
