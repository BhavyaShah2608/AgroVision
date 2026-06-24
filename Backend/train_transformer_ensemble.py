import argparse
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from torch.optim import AdamW
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
from tqdm import tqdm

try:
    import timm
except ImportError as exc:
    raise SystemExit("timm is required. Install with: pip install timm") from exc


@dataclass
class ModelConfig:
    key: str
    timm_name: str


MODEL_ZOO = [
    ModelConfig("vit", "vit_base_patch16_224"),
    ModelConfig("swin", "swin_tiny_patch4_window7_224"),
    ModelConfig("deit", "deit_small_patch16_224"),
]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_transforms(img_size: int) -> Tuple[transforms.Compose, transforms.Compose]:
    train_tfms = transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    val_tfms = transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return train_tfms, val_tfms


def make_consistent_split(
    data_dir: str,
    train_tfms: transforms.Compose,
    val_tfms: transforms.Compose,
    val_ratio: float,
    seed: int,
    max_train_samples: int = 0,
) -> Tuple[Subset, Subset, List[str], List[int], List[int]]:
    ds_for_split = datasets.ImageFolder(data_dir)
    labels = [y for _, y in ds_for_split.samples]
    indices = np.arange(len(labels))

    train_idx, val_idx = train_test_split(
        indices,
        test_size=val_ratio,
        random_state=seed,
        stratify=labels,
    )

    if max_train_samples > 0 and max_train_samples < len(train_idx):
        train_labels = np.array(labels)[train_idx]
        train_idx, _ = train_test_split(
            train_idx,
            train_size=max_train_samples,
            random_state=seed,
            stratify=train_labels,
        )

    train_ds_full = datasets.ImageFolder(data_dir, transform=train_tfms)
    val_ds_full = datasets.ImageFolder(data_dir, transform=val_tfms)

    train_subset = Subset(train_ds_full, train_idx.tolist())
    val_subset = Subset(val_ds_full, val_idx.tolist())

    return train_subset, val_subset, ds_for_split.classes, train_idx.tolist(), val_idx.tolist()


def create_model(
    model_name: str,
    num_classes: int,
    device: torch.device,
    img_size: int = 224,
    freeze_backbone: bool = False,
) -> nn.Module:
    model = timm.create_model(
        model_name,
        pretrained=True,
        num_classes=num_classes,
        img_size=img_size,
        dynamic_img_size=True,
    )

    if freeze_backbone:
        for p in model.parameters():
            p.requires_grad = False

        classifier = model.get_classifier()
        if isinstance(classifier, nn.Module):
            for p in classifier.parameters():
                p.requires_grad = True
        else:
            for name, p in model.named_parameters():
                if any(k in name.lower() for k in ["head", "classifier", "fc"]):
                    p.requires_grad = True

    return model.to(device)


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    losses = []
    for images, targets in tqdm(loader, leave=False):
        images = images.to(device)
        targets = targets.to(device)

        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()

        losses.append(loss.item())

    return float(np.mean(losses)) if losses else 0.0


@torch.no_grad()
def validate(model: nn.Module, loader: DataLoader, device: torch.device) -> Tuple[np.ndarray, np.ndarray]:
    model.eval()
    all_probs = []
    all_targets = []

    for images, targets in tqdm(loader, leave=False):
        images = images.to(device)
        logits = model(images)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
        all_probs.append(probs)
        all_targets.append(targets.numpy())

    probs_np = np.concatenate(all_probs, axis=0)
    targets_np = np.concatenate(all_targets, axis=0)
    return probs_np, targets_np


def train_single_model(
    cfg: ModelConfig,
    train_loader: DataLoader,
    val_loader: DataLoader,
    num_classes: int,
    epochs: int,
    lr: float,
    weight_decay: float,
    device: torch.device,
    out_dir: Path,
    img_size: int,
    freeze_backbone: bool,
) -> Dict[str, object]:
    print(f"\n=== Training {cfg.key} ({cfg.timm_name}) ===")
    model = create_model(
        cfg.timm_name,
        num_classes,
        device,
        img_size=img_size,
        freeze_backbone=freeze_backbone,
    )
    criterion = nn.CrossEntropyLoss()
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    if not trainable_params:
        trainable_params = list(model.parameters())
    optimizer = AdamW(trainable_params, lr=lr, weight_decay=weight_decay)

    best_acc = -1.0
    best_path = out_dir / f"{cfg.key}_best.pt"

    for epoch in range(1, epochs + 1):
        train_loss = run_epoch(model, train_loader, criterion, optimizer, device)
        val_probs, val_targets = validate(model, val_loader, device)
        val_preds = val_probs.argmax(axis=1)
        val_acc = accuracy_score(val_targets, val_preds)
        print(f"Epoch {epoch}/{epochs} | train_loss={train_loss:.4f} | val_acc={val_acc:.4f}")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), best_path)

    model.load_state_dict(torch.load(best_path, map_location=device))
    val_probs, val_targets = validate(model, val_loader, device)

    return {
        "config": cfg,
        "checkpoint": str(best_path),
        "val_probs": val_probs,
        "val_targets": val_targets,
        "best_acc": float(best_acc),
    }


def simplex_weights(n_models: int, step: float = 0.05) -> List[Tuple[float, ...]]:
    units = int(round(1.0 / step))
    combos: List[Tuple[float, ...]] = []

    def rec(remaining: int, slots: int, current: List[int]) -> None:
        if slots == 1:
            combos.append(tuple((current + [remaining])[i] / units for i in range(len(current) + 1)))
            return
        for i in range(remaining + 1):
            rec(remaining - i, slots - 1, current + [i])

    rec(units, n_models, [])
    return combos


def tune_weights(
    probs_list: List[np.ndarray],
    y_true: np.ndarray,
    metric: str = "f1",
) -> Tuple[List[float], float]:
    best_score = -1.0
    best_weights = [1 / len(probs_list)] * len(probs_list)

    for w in simplex_weights(len(probs_list), step=0.05):
        ensemble_probs = np.zeros_like(probs_list[0])
        for i, wi in enumerate(w):
            ensemble_probs += wi * probs_list[i]
        preds = ensemble_probs.argmax(axis=1)
        if metric == "accuracy":
            score = accuracy_score(y_true, preds)
        else:
            score = f1_score(y_true, preds, average="macro")

        if score > best_score:
            best_score = float(score)
            best_weights = [float(x) for x in w]

    return best_weights, best_score


def tune_unknown_threshold(
    ensemble_probs: np.ndarray,
    y_true: np.ndarray,
    min_threshold: float = 0.30,
    max_threshold: float = 0.90,
    step: float = 0.01,
) -> Tuple[float, Dict[str, float]]:
    best_t = 0.5
    best_metric = -1.0
    best_stats = {"coverage": 0.0, "accepted_accuracy": 0.0, "combined": 0.0}

    thresholds = np.arange(min_threshold, max_threshold + 1e-9, step)
    pred_cls = ensemble_probs.argmax(axis=1)
    pred_conf = ensemble_probs.max(axis=1)

    for t in thresholds:
        accepted = pred_conf >= t
        coverage = float(accepted.mean())
        if accepted.sum() == 0:
            continue

        accepted_acc = accuracy_score(y_true[accepted], pred_cls[accepted])
        combined = accepted_acc * coverage

        if combined > best_metric:
            best_metric = combined
            best_t = float(t)
            best_stats = {
                "coverage": coverage,
                "accepted_accuracy": float(accepted_acc),
                "combined": float(combined),
            }

    return best_t, best_stats


def evaluate_with_threshold(
    probs: np.ndarray,
    y_true: np.ndarray,
    class_names: List[str],
    threshold: float,
) -> Dict[str, object]:
    pred_cls = probs.argmax(axis=1)
    pred_conf = probs.max(axis=1)
    pred_labels = np.array([class_names[i] if c >= threshold else "Unknown" for i, c in zip(pred_cls, pred_conf)])
    true_labels = np.array([class_names[i] for i in y_true])

    accepted = pred_labels != "Unknown"
    accepted_accuracy = float(accuracy_score(true_labels[accepted], pred_labels[accepted])) if accepted.any() else 0.0
    overall_accuracy = float((pred_labels == true_labels).mean())

    labels_for_report = class_names + ["Unknown"]
    cm = confusion_matrix(true_labels, pred_labels, labels=labels_for_report)
    report = classification_report(true_labels, pred_labels, labels=labels_for_report, zero_division=0)

    return {
        "accepted_accuracy": accepted_accuracy,
        "overall_accuracy": overall_accuracy,
        "coverage": float(accepted.mean()),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }


def evaluate_external_folder(
    probs: np.ndarray,
    class_names: List[str],
    threshold: float,
) -> Dict[str, float]:
    pred_cls = probs.argmax(axis=1)
    pred_conf = probs.max(axis=1)
    known_rate = float((pred_conf >= threshold).mean())
    top1_mean_conf = float(pred_conf.mean())
    top1_std_conf = float(pred_conf.std())

    counts = {name: 0 for name in class_names}
    for idx, conf in zip(pred_cls, pred_conf):
        if conf >= threshold:
            counts[class_names[idx]] += 1

    return {
        "predicted_known_rate": known_rate,
        "mean_top1_confidence": top1_mean_conf,
        "std_top1_confidence": top1_std_conf,
        "known_class_counts": counts,
    }


def load_images_from_flat_folder(folder: str, transform: transforms.Compose):
    from PIL import Image

    images = []
    valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if Path(name).suffix.lower() not in valid_ext:
            continue
        img = Image.open(path).convert("RGB")
        images.append(transform(img))

    if not images:
        return None
    return torch.stack(images, dim=0)


@torch.no_grad()
def predict_probs_for_tensor_batch(
    model_infos: List[Dict[str, object]],
    x: torch.Tensor,
    device: torch.device,
) -> List[np.ndarray]:
    probs_list = []
    for info in model_infos:
        cfg = info["config"]
        model = create_model(
            cfg.timm_name,
            info["num_classes"],
            device,
            img_size=info.get("img_size", 224),
        )
        model.load_state_dict(torch.load(info["checkpoint"], map_location=device))
        model.eval()

        logits = model(x.to(device))
        probs = torch.softmax(logits, dim=1).cpu().numpy()
        probs_list.append(probs)

    return probs_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train ViT + Swin + DeiT ensemble for plant disease classification")
    parser.add_argument("--data-dir", type=str, default="plantvillage dataset/color")
    parser.add_argument("--output-dir", type=str, default="ensemble_artifacts")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--metric", type=str, choices=["f1", "accuracy"], default="f1")
    parser.add_argument("--external-folder", type=str, default="")
    parser.add_argument("--models", nargs="+", choices=["vit", "swin", "deit"], default=["vit", "swin", "deit"])
    parser.add_argument("--freeze-backbone", action="store_true")
    parser.add_argument("--max-train-samples", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_tfms, val_tfms = build_transforms(args.img_size)
    train_ds, val_ds, class_names, train_idx, val_idx = make_consistent_split(
        args.data_dir,
        train_tfms,
        val_tfms,
        args.val_ratio,
        args.seed,
        args.max_train_samples,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    num_classes = len(class_names)
    print(f"Classes: {num_classes}")
    print(f"Train size: {len(train_ds)} | Val size: {len(val_ds)}")
    print(f"Models: {args.models}")

    selected_cfgs = [cfg for cfg in MODEL_ZOO if cfg.key in args.models]
    if not selected_cfgs:
        raise ValueError("No valid models selected")

    model_infos: List[Dict[str, object]] = []
    for cfg in selected_cfgs:
        info = train_single_model(
            cfg=cfg,
            train_loader=train_loader,
            val_loader=val_loader,
            num_classes=num_classes,
            epochs=args.epochs,
            lr=args.lr,
            weight_decay=args.weight_decay,
            device=device,
            out_dir=out_dir,
            img_size=args.img_size,
            freeze_backbone=args.freeze_backbone,
        )
        info["num_classes"] = num_classes
        info["img_size"] = args.img_size
        model_infos.append(info)

    y_true = model_infos[0]["val_targets"]
    probs_list = [m["val_probs"] for m in model_infos]

    weights, best_metric = tune_weights(probs_list, y_true, metric=args.metric)
    ensemble_probs = np.zeros_like(probs_list[0])
    for i, wi in enumerate(weights):
        ensemble_probs += wi * probs_list[i]

    threshold, threshold_stats = tune_unknown_threshold(ensemble_probs, y_true)
    eval_stats = evaluate_with_threshold(ensemble_probs, y_true, class_names, threshold)

    print("\n=== Ensemble Summary ===")
    print(f"Weights: {weights}")
    print(f"Best val {args.metric}: {best_metric:.4f}")
    print(f"Unknown threshold: {threshold:.2f}")
    print(f"Coverage: {eval_stats['coverage']:.4f}")
    print(f"Accepted accuracy: {eval_stats['accepted_accuracy']:.4f}")
    print(f"Overall accuracy (unknown counts as wrong): {eval_stats['overall_accuracy']:.4f}")
    print("\nClassification report:")
    print(eval_stats["classification_report"])

    result = {
        "class_names": class_names,
        "models": [
            {
                "name": m["config"].key,
                "timm_name": m["config"].timm_name,
                "checkpoint": m["checkpoint"],
                "best_val_acc": m["best_acc"],
                "img_size": m.get("img_size", args.img_size),
            }
            for m in model_infos
        ],
        "weights": {m["config"].key: weights[i] for i, m in enumerate(model_infos)},
        "weight_tuning_metric": args.metric,
        "best_weight_metric_value": best_metric,
        "unknown_threshold": threshold,
        "threshold_stats": threshold_stats,
        "evaluation": {
            "coverage": eval_stats["coverage"],
            "accepted_accuracy": eval_stats["accepted_accuracy"],
            "overall_accuracy": eval_stats["overall_accuracy"],
            "confusion_matrix": eval_stats["confusion_matrix"],
            "classification_report": eval_stats["classification_report"],
        },
        "split": {
            "seed": args.seed,
            "val_ratio": args.val_ratio,
            "train_indices": train_idx,
            "val_indices": val_idx,
        },
    }

    if args.external_folder:
        ext_batch = load_images_from_flat_folder(args.external_folder, val_tfms)
        if ext_batch is not None:
            ext_probs_list = predict_probs_for_tensor_batch(model_infos, ext_batch, device)
            ext_ensemble_probs = np.zeros_like(ext_probs_list[0])
            for i, wi in enumerate(weights):
                ext_ensemble_probs += wi * ext_probs_list[i]
            ext_stats = evaluate_external_folder(ext_ensemble_probs, class_names, threshold)
            result["external_folder"] = {
                "path": args.external_folder,
                "num_images": int(ext_batch.shape[0]),
                "stats": ext_stats,
            }
            print("\nExternal folder stats:")
            print(json.dumps(result["external_folder"], indent=2))
        else:
            print("\nNo valid images found in external folder, skipping external evaluation.")

    with open(out_dir / "ensemble_config.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved config to: {out_dir / 'ensemble_config.json'}")


if __name__ == "__main__":
    main()
