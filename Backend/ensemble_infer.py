import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

try:
    import timm
except ImportError as exc:
    raise SystemExit("timm is required. Install with: pip install timm") from exc


class TransformerEnsemble:
    def __init__(self, config_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.class_names: List[str] = cfg["class_names"]
        self.unknown_threshold: float = float(cfg["unknown_threshold"])
        self.weights: Dict[str, float] = cfg["weights"]

        self.models: List[torch.nn.Module] = []
        self.model_names: List[str] = []
        self.model_weights: List[float] = []

        base_dir = Path(config_path).parent
        for m in cfg["models"]:
            timm_name = m["timm_name"]
            checkpoint = Path(m["checkpoint"])
            if not checkpoint.is_absolute():
                checkpoint = base_dir / checkpoint

            model = timm.create_model(timm_name, pretrained=False, num_classes=len(self.class_names))
            model.load_state_dict(torch.load(str(checkpoint), map_location=self.device))
            model.to(self.device)
            model.eval()

            self.models.append(model)
            self.model_names.append(m["name"])
            self.model_weights.append(float(self.weights[m["name"]]))

        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    @torch.no_grad()
    def predict(self, image_path: str) -> Dict[str, object]:
        image = Image.open(image_path).convert("RGB")
        x = self.transform(image).unsqueeze(0).to(self.device)

        probs_list = []
        per_model = {}
        for model, name in zip(self.models, self.model_names):
            logits = model(x)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            probs_list.append(probs)

            pred_idx = int(np.argmax(probs))
            per_model[name] = {
                "class": self.class_names[pred_idx],
                "confidence": float(probs[pred_idx]),
            }

        ensemble_probs = np.zeros_like(probs_list[0])
        for w, p in zip(self.model_weights, probs_list):
            ensemble_probs += w * p

        pred_idx = int(np.argmax(ensemble_probs))
        confidence = float(ensemble_probs[pred_idx])
        label = self.class_names[pred_idx] if confidence >= self.unknown_threshold else "Unknown"

        topk = np.argsort(ensemble_probs)[::-1][:3]
        top3 = [
            {
                "class": self.class_names[int(i)],
                "confidence": float(ensemble_probs[int(i)]),
            }
            for i in topk
        ]

        return {
            "prediction": label,
            "confidence": confidence,
            "threshold": self.unknown_threshold,
            "top3": top3,
            "per_model": per_model,
        }


def load_ensemble(config_path: str = "ensemble_artifacts/ensemble_config.json") -> TransformerEnsemble:
    return TransformerEnsemble(config_path)


def predict_image(
    image_path: str,
    config_path: str = "ensemble_artifacts/ensemble_config.json",
) -> Dict[str, object]:
    ensemble = TransformerEnsemble(config_path)
    return ensemble.predict(image_path)
