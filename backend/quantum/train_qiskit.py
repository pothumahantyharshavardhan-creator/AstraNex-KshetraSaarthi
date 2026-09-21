"""Reproducible training entry point for the AstraNex quantum layer.

    python -m backend.quantum.train_qiskit                    # trains in whatever mode is active
    python -m backend.quantum.train_qiskit --require-qiskit   # refuse unless Qiskit ML really executes

Whatever ran is recorded in the artifacts (mode, execution_label, qiskit_execution), so a
fallback-simulator run can never be mistaken for a Qiskit run.
"""
from __future__ import annotations
import argparse
from . import benchmark
from .quantum_classifier import quantum_runtime_status


def main() -> int:
    ap = argparse.ArgumentParser(description="Train the AstraNex quantum + classical models and write the benchmark")
    ap.add_argument("--dataset-size", type=int, default=360)
    ap.add_argument("--iterations", type=int, default=120)
    ap.add_argument("--require-qiskit", action="store_true",
                    help="fail unless the real Qiskit Machine Learning EstimatorQNN path is active")
    args = ap.parse_args()
    rt = quantum_runtime_status()
    print("execution mode :", rt["mode"], "-", rt["execution_label"])
    if rt.get("import_error"):
        print("note           :", rt["import_error"])
    result = benchmark.run_benchmark(dataset_size=args.dataset_size, iterations=args.iterations,
                                     require_qiskit=args.require_qiskit, save=True)
    print("training complete")
    print("backend        :", result["execution_backend"])
    print("qiskit executed:", result["qiskit_execution"])
    print("quantum acc    : %.2f%%   classical acc: %.2f%%" % (
        result["quantum"]["metrics"]["accuracy"], result["classical"]["metrics"]["accuracy"]))
    print("benchmark file :", benchmark.result_file(result["mode"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
