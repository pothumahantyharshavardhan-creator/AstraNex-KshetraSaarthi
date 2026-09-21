# AstraNex vision model

The application uses the published FP32 `cropguard.onnx` ResNet50 PlantVillage model. The model is not committed to this ZIP because it is about 94 MB.

From the project root, with the virtual environment active:

```bash
python scripts/download_model.py
```

The backend also attempts the same download automatically on first real-image analysis when internet access is available.

Important: PlantVillage contains 38 classes across 14 crops and was photographed under controlled conditions. It is a screening component, not a field-validated Indian crop diagnosis model.
