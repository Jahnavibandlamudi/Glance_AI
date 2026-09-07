import argparse
import random
import time
import json
import hashlib
from pathlib import Path

import joblib
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageOps
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from torchvision import models


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def build_feature_extractor(name: str):
    if name == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT
        model = models.efficientnet_b0(weights=weights)
        model.classifier = torch.nn.Identity()
    elif name == "mobilenet_v3_small":
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        model = models.mobilenet_v3_small(weights=weights)
        model.classifier = torch.nn.Identity()
    else:
        raise ValueError(f"Unsupported feature model: {name}")

    model.eval()
    return model, weights


def image_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]


def sample_files(folder: Path, limit: int, seed: int) -> list[Path]:
    files = image_files(folder)
    random.Random(seed).shuffle(files)
    return files[:limit]


def open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def feedback_variants(image: Image.Image) -> list[Image.Image]:
    variants = [image]
    variants.append(ImageEnhance.Brightness(image).enhance(0.88))
    variants.append(ImageEnhance.Brightness(image).enhance(1.12))
    variants.append(ImageEnhance.Contrast(image).enhance(0.9))
    variants.append(ImageEnhance.Contrast(image).enhance(1.1))
    variants.append(ImageOps.mirror(image))
    width, height = image.size
    if width >= 320 and height >= 240:
        crop = image.crop((width * 0.05, height * 0.05, width * 0.95, height * 0.95))
        variants.append(crop.resize((width, height)))
    return variants


def build_rows(
    dataset_root: Path,
    feedback_root: Path,
    per_class: int,
    seed: int,
    feedback_repeat: int,
):
    train_root = dataset_root / "train"
    if not train_root.exists():
        train_root = dataset_root

    real_train = sample_files(train_root / "real", per_class, seed)
    fake_train = sample_files(train_root / "fake", per_class, seed + 1)

    test_root = dataset_root / "test"
    real_test = sample_files(test_root / "real", max(200, per_class // 5), seed + 2)
    fake_test = sample_files(test_root / "fake", max(200, per_class // 5), seed + 3)

    feedback_real = image_files(feedback_root / "real")
    feedback_ai = image_files(feedback_root / "ai")

    train_rows = [(path, 0, False) for path in real_train]
    train_rows += [(path, 1, False) for path in fake_train]
    for _ in range(feedback_repeat):
        train_rows += [(path, 0, True) for path in feedback_real]
        train_rows += [(path, 1, True) for path in feedback_ai]

    test_rows = [(path, 0) for path in real_test] + [(path, 1) for path in fake_test]
    feedback_rows = [(path, 0) for path in feedback_real] + [(path, 1) for path in feedback_ai]
    return train_rows, test_rows, feedback_rows


def extract_features(rows, model, transform, device, augment_feedback: bool):
    features = []
    labels = []
    with torch.no_grad():
        for index, row in enumerate(rows, start=1):
            if len(row) == 3:
                path, label, is_feedback = row
            else:
                path, label = row
                is_feedback = False

            image = open_rgb(path)
            images = feedback_variants(image) if augment_feedback and is_feedback else [image]
            for candidate in images:
                tensor = transform(candidate).unsqueeze(0).to(device)
                feature = model(tensor).detach().cpu().numpy()[0]
                features.append(feature)
                labels.append(label)

            if index % 250 == 0:
                print(f"extracted {index}/{len(rows)} rows")

    return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64)


def batched_features(rows, model, transform, device):
    features = []
    with torch.inference_mode():
        for start in range(0, len(rows), 32):
            batch = rows[start:start + 32]
            tensors = torch.stack([transform(open_rgb(row[0])) for row in batch]).to(device)
            features.append(model(tensors).cpu().numpy())
            if start % 512 == 0:
                print(f"extracted {start + len(batch)}/{len(rows)}", flush=True)
    return np.concatenate(features), np.asarray([row[1] for row in rows])


def training_features(rows, model, transform, device):
    standard_rows = [(path, label) for path, label, is_feedback in rows if not is_feedback]
    feedback_rows = [(path, label, is_feedback) for path, label, is_feedback in rows if is_feedback]
    features, labels = batched_features(standard_rows, model, transform, device)
    if not feedback_rows:
        return features, labels
    feedback_features, feedback_labels = extract_features(
        feedback_rows,
        model,
        transform,
        device,
        augment_feedback=True,
    )
    return (
        np.concatenate([features, feedback_features]),
        np.concatenate([labels, feedback_labels]),
    )


def evaluate(classifier, features, labels):
    probabilities = classifier.predict_proba(features)[:, 1]
    predictions = (probabilities >= 0.5).astype(np.int64)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average=None,
        labels=[0, 1],
        zero_division=0,
    )
    return {
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "log_loss": float(log_loss(labels, probabilities)),
        "accuracy": float(accuracy_score(labels, predictions)),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
        "real_precision": float(precision[0]),
        "real_recall": float(recall[0]),
        "real_f1": float(f1[0]),
        "fake_precision": float(precision[1]),
        "fake_recall": float(recall[1]),
        "fake_f1": float(f1[1]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default="backend/data/raw/140k/real_vs_fake/real-vs-fake")
    parser.add_argument("--feedback-root", default="backend/data/feedback")
    parser.add_argument("--output", default="backend/models/visual_ai_detector.joblib")
    parser.add_argument("--per-class", type=int, default=5000)
    parser.add_argument("--feedback-repeat", type=int, default=1)
    parser.add_argument("--feature-model", default="efficientnet_b0")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.feedback_repeat != 1:
        raise ValueError("Feedback must appear once; repeating corrections can cause memorization.")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(min(4, torch.get_num_threads()))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    feature_model, weights = build_feature_extractor(args.feature_model)
    feature_model.to(device)

    train_rows, test_rows, feedback_rows = build_rows(
        Path(args.dataset_root),
        Path(args.feedback_root),
        args.per_class,
        args.seed,
        args.feedback_repeat,
    )

    print(f"training rows: {len(train_rows)}; test rows: {len(test_rows)}; feedback rows: {len(feedback_rows)}")
    valid_root = Path(args.dataset_root) / "valid"
    valid_rows = [(p, label) for label, folder in enumerate(("real", "fake"))
                  for p in sample_files(valid_root / folder, 1000, args.seed + 10 + label)]
    if any(set(row[1] for row in rows) != {0, 1} for rows in (train_rows, valid_rows, test_rows)):
        raise ValueError("Train, valid and test must each contain both real and fake images.")
    split_hashes = [{hashlib.sha256(row[0].read_bytes()).hexdigest() for row in rows}
                    for rows in (train_rows, valid_rows, test_rows)]
    if any(split_hashes[a] & split_hashes[b] for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Duplicate images cross training/calibration/test boundaries.")
    train_features, train_labels = training_features(
        train_rows,
        feature_model,
        weights.transforms(),
        device,
    )
    test_features, test_labels = batched_features(
        test_rows,
        feature_model,
        weights.transforms(),
        device,
    )

    classifier = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=0.01,
            max_iter=1000,
            class_weight="balanced",
            random_state=args.seed,
        ),
    )
    classifier.fit(train_features, train_labels)

    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.frozen import FrozenEstimator
    valid_features, valid_labels = batched_features(valid_rows, feature_model, weights.transforms(), device)
    classifier = CalibratedClassifierCV(FrozenEstimator(classifier), method="sigmoid").fit(valid_features, valid_labels)

    test_summary = evaluate(classifier, test_features, test_labels)
    feedback_summary = None
    if feedback_rows:
        feedback_features, feedback_labels = extract_features(
            feedback_rows,
            feature_model,
            weights.transforms(),
            device,
            augment_feedback=False,
        )
        feedback_summary = evaluate(classifier, feedback_features, feedback_labels)

    artifact = {
        "classifier": classifier,
        "training_summary": {
            "dataset": str(Path(args.dataset_root)),
            "feedback": str(Path(args.feedback_root)),
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "feedback_rows": len(feedback_rows),
            "per_class": args.per_class,
            "feedback_repeat": args.feedback_repeat,
            "feature_model_key": args.feature_model,
            "test": test_summary,
            "feedback_training_check_only": feedback_summary,
            "calibration_rows": len(valid_rows),
            "scope": "Real-vs-fake face dataset; modern generators and camera replay are not validated.",
            "thresholds": {
                "likely_genuine_max_ai_probability": 0.35,
                "likely_ai_min_ai_probability": 0.65,
            },
            "feature_model": f"torchvision {args.feature_model} frozen ImageNet embeddings + calibrated logistic classifier",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output)
    output.with_suffix(".json").write_text(json.dumps(artifact["training_summary"], indent=2))
    print(f"saved {output}")
    print(artifact["training_summary"])


if __name__ == "__main__":
    main()
