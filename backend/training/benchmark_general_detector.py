"""Benchmark a pinned pretrained detector locally without training on the target."""
import argparse
import json
import time
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from PIL import Image, ImageOps
from sklearn.metrics import accuracy_score, confusion_matrix
from transformers import AutoImageProcessor, AutoModelForImageClassification

MODELS = {
    "siglip": {
        "model_id": "Ateeqq/ai-vs-human-image-detector",
        "revision": "60e82406916921b823616bee33397baab38af3f0",
        "destination": Path("backend/models/siglip_general"),
        "ai_label": "ai",
        "report": Path("backend/models/general_benchmark.json"),
    },
    "sdxl_swin": {
        "model_id": "Organika/sdxl-detector",
        "revision": "ad18a48c10c4f5bc8a98ed42a68d875d6df786a6",
        "destination": Path("backend/models/sdxl_swin_detector"),
        "ai_label": "artificial",
        "report": Path("backend/models/sdxl_swin_benchmark.json"),
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=sorted(MODELS), default="siglip")
    parser.add_argument("--limit-per-class", type=int, default=100)
    args = parser.parse_args()
    config = MODELS[args.model]
    torch.set_num_threads(4)
    snapshot_download(config["model_id"], revision=config["revision"], local_dir=config["destination"],
                      allow_patterns=["config.json", "preprocessor_config.json", "model.safetensors", "README.md"])
    processor = AutoImageProcessor.from_pretrained(config["destination"], local_files_only=True)
    model = AutoModelForImageClassification.from_pretrained(config["destination"], local_files_only=True,
                                                          use_safetensors=True, trust_remote_code=False).eval()
    labels = {int(index): label.lower() for index, label in model.config.id2label.items()}
    ai_index = next(index for index, label in labels.items() if label == config["ai_label"])
    rows = [(Path(r"C:\Users\bnsja\OneDrive\Documents\AI image.webp"), 1, "user_example")]
    for label, folder in [(0, "real"), (1, "ai")]:
        rows += [(p, label, "feedback") for p in Path("backend/data/feedback", folder).glob("*")]
    root = Path("backend/data/raw/140k/real_vs_fake/real-vs-fake/test")
    for label, folder in enumerate(("real", "fake")):
        rows += [(p, label, "face_test") for p in sorted((root/folder).glob("*.jpg"))[:args.limit_per_class]]
    results = []
    with torch.inference_mode():
        for start in range(0, len(rows), 8):
            batch = rows[start:start+8]
            images = []
            for path, _, _ in batch:
                with Image.open(path) as image:
                    images.append(ImageOps.exif_transpose(image).convert("RGB"))
            t = time.perf_counter()
            probabilities = model(**processor(images=images, return_tensors="pt")).logits.softmax(-1)[:, ai_index].tolist()
            for (path, label, group), probability in zip(batch, probabilities):
                result = dict(filename=path.name, label=label, group=group, ai_probability=probability)
                results.append(result)
                if group != "face_test":
                    print(result, flush=True)
            print(f"Completed {min(start+8,len(rows))}/{len(rows)} ({time.perf_counter()-t:.2f}s/batch)", flush=True)
    subset = [r for r in results if r["group"] == "face_test"]
    truth = [r["label"] for r in subset]
    predicted = [int(r["ai_probability"] >= .5) for r in subset]
    report = dict(model_id=config["model_id"], revision=config["revision"], id2label=model.config.id2label,
                  ai_index=ai_index, rows=results,
                  face_test_accuracy=accuracy_score(truth, predicted),
                  face_test_confusion=confusion_matrix(truth,predicted).tolist())
    config["report"].write_text(json.dumps(report,indent=2))
    print({k:v for k,v in report.items() if k != "rows"}, flush=True)


if __name__ == "__main__":
    main()
