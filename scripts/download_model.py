"""Download and validate the published CropGuard PlantVillage serving artifacts."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "backend" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPO = "AbhiCommits/cropguard-models"
MODEL_NAME = "cropguard.onnx"
CLASSES_NAME = "classes.json"

model_path = Path(hf_hub_download(REPO, MODEL_NAME, local_dir=MODEL_DIR))
classes_path = Path(hf_hub_download(REPO, CLASSES_NAME, local_dir=MODEL_DIR))
labels = json.loads(classes_path.read_text(encoding="utf-8"))
if isinstance(labels, dict):
    labels = labels.get("classes") or labels.get("labels") or list(labels.values())
if not isinstance(labels, list) or len(labels) != 38:
    raise SystemExit(f"Invalid class map: expected 38 labels, got {len(labels) if isinstance(labels,list) else 'non-list'}")
sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
manifest = {
    "name": "CropGuard ResNet50 ONNX FP32",
    "dataset": "PlantVillage",
    "model_file": model_path.name,
    "classes_file": classes_path.name,
    "class_count": len(labels),
    "sha256": sha256,
    "source_repo": REPO,
    "field_validation_status": "not_validated"
}
(MODEL_DIR / "MODEL_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Model: {model_path}")
print(f"Classes: {classes_path}")
print(f"SHA256: {sha256}")
print("Class count: 38")
