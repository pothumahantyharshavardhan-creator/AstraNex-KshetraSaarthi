"""Verify that the persisted quantum artifacts are self-consistent and honestly labelled.

    python scripts/verify_quantum.py                   # checks the artifacts for the ACTIVE mode
    python scripts/verify_quantum.py --require-qiskit  # additionally fail unless real Qiskit executed
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.quantum import benchmark, qiskit_vqc                       # noqa: E402
from backend.quantum.quantum_classifier import QuantumClassifier, quantum_runtime_status  # noqa: E402
from backend.quantum.classical_baseline import ClassicalBaseline        # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-qiskit", action="store_true")
    args = ap.parse_args()
    rt = quantum_runtime_status()
    print("execution mode :", rt["mode"], "-", rt["execution_label"])
    print("qiskit runtime :", qiskit_vqc.runtime_report())
    if args.require_qiskit and not rt["qiskit_execution"]:
        print("FAIL: --require-qiskit given but Qiskit is not the active execution engine.")
        return 2
    saved = benchmark.load_result()
    if saved is None:
        print("FAIL: no valid benchmark artifact for this mode:", benchmark.result_file(rt["mode"]).name,
              "\n      run: python -m backend.quantum.train_qiskit")
        return 2
    if saved.get("mode") != rt["mode"]:
        print("FAIL: benchmark was produced in mode", saved.get("mode"), "but the active mode is", rt["mode"])
        return 2
    if saved["qiskit_execution"] != rt["qiskit_execution"]:
        print("FAIL: benchmark qiskit_execution flag disagrees with the active runtime.")
        return 2
    if rt["mode"] == "qiskit_machine_learning":
        m = qiskit_vqc.QiskitVQC.load(expected_features=None)
        if m is None:
            print("FAIL: trained_qiskit_model.json is missing or invalid."); return 2
        ok, errors = m.validate(expected_features=saved["features"]["selected"])
    else:
        m = QuantumClassifier.load()
        if m is None:
            print("FAIL: trained_model.json is missing or invalid."); return 2
        ok, errors = m.validate(expected_features=saved["features"]["selected"]) if hasattr(m, "validate") else (True, [])
    if not ok:
        print("FAIL:", errors); return 2
    c = ClassicalBaseline.load()
    if c is None or list(c.features) != list(saved["features"]["selected"]):
        print("FAIL: classical baseline is missing or uses a different feature set."); return 2
    print("PASS: model + benchmark verified for mode '%s' (quantum %.2f%% / classical %.2f%%, qiskit_execution=%s)." % (
        rt["mode"], saved["quantum"]["metrics"]["accuracy"], saved["classical"]["metrics"]["accuracy"], saved["qiskit_execution"]))
    if not rt["qiskit_execution"]:
        print("NOTE: this is the built-in simulator, not Qiskit. Install requirements.txt for a Qiskit run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
