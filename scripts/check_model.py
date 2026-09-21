"""Validate the optional local CropGuard ONNX model without fabricating readiness."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'backend/models/cropguard.onnx'
CLASSES=ROOT/'backend/models/classes.json'
EXPECTED=38

def main():
    print('AstraNex vision-model preflight')
    if not MODEL.exists():
        print('MODEL: MISSING')
        print('Run: python scripts/download_model.py')
        return 2
    print('MODEL:', MODEL)
    print('SHA256:', hashlib.sha256(MODEL.read_bytes()).hexdigest())
    if not CLASSES.exists():
        print('CLASSES: MISSING')
        return 2
    try:
        labels=json.loads(CLASSES.read_text(encoding='utf-8'))
        if isinstance(labels,dict): labels=labels.get('classes') or labels.get('labels') or list(labels.values())
        if not isinstance(labels,list) or len(labels)!=EXPECTED:
            print(f'CLASSES: INVALID (expected {EXPECTED}, got {len(labels) if isinstance(labels,list) else "non-list"})')
            return 2
        print('CLASSES: OK (38)')
    except Exception as exc:
        print('CLASSES: INVALID', type(exc).__name__, exc); return 2
    try:
        import onnxruntime as ort
        s=ort.InferenceSession(str(MODEL), providers=['CPUExecutionProvider'])
        inp=s.get_inputs()[0]
        shape=[x if isinstance(x,int) else None for x in inp.shape]
        print('ONNX Runtime: OK')
        print('INPUT:', inp.name, shape, inp.type)
        print('OUTPUTS:', len(s.get_outputs()))
    except Exception as exc:
        print('ONNX Runtime: INVALID/UNAVAILABLE', type(exc).__name__, exc); return 2
    print('VISION MODEL: READY FOR SCREENING (not field-validated)')
    return 0

if __name__=='__main__': raise SystemExit(main())
