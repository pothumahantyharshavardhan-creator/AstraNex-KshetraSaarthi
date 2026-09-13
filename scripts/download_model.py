from huggingface_hub import hf_hub_download
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "backend" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
path = hf_hub_download("AbhiCommits/cropguard-models", "cropguard.onnx", local_dir=MODEL_DIR)
classes = hf_hub_download("AbhiCommits/cropguard-models", "classes.json", local_dir=MODEL_DIR)
print(f"Model: {path}")
print(f"Classes: {classes}")
