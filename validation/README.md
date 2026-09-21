# AstraNex field-validation dataset

This folder is intentionally empty of fabricated agricultural ground truth. To establish a real field-accuracy result, collect expert-verified samples and place a CSV at `validation/field_labels.csv` using the template columns below.

Required columns:
- `sample_id`
- `crop`
- `true_label`
- `predicted_label`
- `confidence` (0–1)
- `split` (`train`, `validation`, or `test`)
- `location_state`
- `capture_condition`

Recommended additional metadata: device/camera, growth stage, image quality, lighting, expert identifier, date, and whether the sample was captured in a farmer field.

Run:

```bash
python scripts/validate_field_dataset.py validation/field_labels.csv
```

The report computes overall and per-class precision/recall/F1, balanced accuracy, coverage, abstention rate, and a confusion matrix. It does **not** turn the demonstration dataset into field accuracy and it does not produce a 95–99% claim unless the supplied field-labelled data actually supports that result.
