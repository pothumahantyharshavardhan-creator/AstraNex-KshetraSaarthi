"""AstraNex final release preflight with separate demo/field/QML gates."""
from __future__ import annotations
import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def module(n): return importlib.util.find_spec(n) is not None
def main():
    q=module('qiskit'); qml=module('qiskit_machine_learning'); ort=module('onnxruntime')
    vision=(ROOT/'backend/models/cropguard.onnx').exists(); classes=(ROOT/'backend/models/classes.json').exists()
    qmodel=(ROOT/'backend/quantum/trained_qiskit_model.json').exists(); bench=(ROOT/'backend/quantum/benchmark_result.json').exists()
    sim_bench=(ROOT/'backend/quantum/benchmark_result_fallback_simulation.json').exists(); sim_model=(ROOT/'backend/quantum/trained_model.json').exists()
    field_report=(ROOT/'validation/field_validation_report.json').exists()
    print('AstraNex KshetraSaarthi v3.2 final preflight')
    print(f'  Demo backend/source: OK')
    print(f'  ONNX Runtime: {"OK" if ort else "MISSING"}')
    print(f'  Vision weights: {"OK" if vision else "MISSING"}')
    print(f'  Vision class map: {"OK" if classes else "MISSING"}')
    print(f'  Qiskit: {"OK" if q else "MISSING"}')
    print(f'  Qiskit Machine Learning: {"OK" if qml else "MISSING"}')
    print(f'  QML trained artifact: {"OK" if qmodel else "MISSING"}')
    print(f'  QML benchmark: {"OK" if bench else "MISSING"}')
    print(f'  Built-in simulator model + benchmark (labelled, not Qiskit): {"OK" if sim_bench and sim_model else "MISSING"}')
    print(f'  Field validation report: {"OK" if field_report else "NOT ESTABLISHED"}')
    demo=True; field=ort and vision and classes; qml_ready=q and qml and qmodel and bench
    print('  demo readiness: READY')
    print('  field vision readiness:', 'READY' if field else 'PREREQUISITES PENDING')
    print('  production QML readiness:', 'READY' if qml_ready else 'PREREQUISITES PENDING')
    print('  field-validation evidence:', 'AVAILABLE' if field_report else 'NOT ESTABLISHED')
    return 0 if demo and field and qml_ready and field_report else 2
if __name__=='__main__': raise SystemExit(main())
