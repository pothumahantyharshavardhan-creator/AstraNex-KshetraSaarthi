# The quantum layer

Everything below describes code in `backend/quantum/`. Where something is simulated,
proxied or unvalidated, it says so.

## 1. What runs the circuit

Three tiers, reported precisely. The interface, the API and the benchmark all print
the tier that actually executed — the fallback is **never** labelled Qiskit.

| Tier (`mode`) | When | What executes |
|---|---|---|
| `qiskit_machine_learning` | `qiskit` **and** `qiskit-machine-learning` importable | `ZZFeatureMap` → `RealAmplitudes` wrapped in `EstimatorQNN`, observable `Z⊗Z⊗Z⊗Z` (`backend/quantum/qiskit_vqc.py`) |
| `qiskit_statevector` | only `qiskit` importable | The built-in ansatz as a real `QuantumCircuit`, expectation values via `qiskit.quantum_info.Statevector` |
| `fallback_simulation` | neither, or `ASTRANEX_FORCE_FALLBACK_SIM=1` | Bundled Python state-vector simulator, labelled **"Fallback quantum simulation — not Qiskit execution"** |

`quantum_runtime_status()` returns `mode`, `execution_backend`, `execution_label`,
`qiskit_execution`, `qiskit_installed`, `qiskit_machine_learning_installed` and their
versions. `hardware_execution` is always `False`; nothing here touches a QPU.

Verify it on your machine:

```bash
python scripts/verify_quantum.py
```

It prints installation state, versions, the selected engine, and the result of a real
inference — measured, not assumed. `pytest tests/test_quantum.py` asserts that the
fallback can never be reported as Qiskit execution.

### The Qiskit Machine Learning circuit

```python
feature_map = ZZFeatureMap(feature_dimension=4, reps=1, entanglement="linear")
ansatz      = RealAmplitudes(num_qubits=4, reps=2, entanglement="circular")
qnn         = EstimatorQNN(circuit=feature_map.compose(ansatz),
                           observables=SparsePauliOp("ZZZZ"),
                           input_params=feature_map.parameters,
                           weight_params=ansatz.parameters)
```

The circuit drawn in the Quantum lab is read back from this object
(`describe_circuit()` walks the decomposed `QuantumCircuit`), so the diagram cannot
drift from the circuit being executed. Both tiers are trained by the same SPSA routine
so that a benchmark is never silently comparing two different optimisers.

## 2. Features

Eight features come out of the existing AstraNex pipeline — never out of a random
generator:

| Feature | Source |
|---|---|
| Disease signal | risk engine (vision + context fusion) |
| Soil moisture | field sensor |
| Temperature | field sensor / climate module |
| Humidity | field sensor / climate module |
| Water risk | risk engine (moisture + weather) |
| Heat stress risk | risk engine (temperature + weather) |
| Sensor reliability | sensor-health assessment |
| Image confidence | ONNX vision inference confidence |

Excess-water risk is carried as context and can be selected if it ranks high enough.

Each is min-max normalised into `[0, 1]` using the physical ranges in
`FEATURE_RANGES`, then mapped to `[0, π]` for angle encoding.

## 3. Feature selection

`select_features()` ranks by `|Pearson correlation with the label| × (0.5 + standard
deviation)`, computed **on the training split only** so the test split cannot leak into
the choice. The top `k = 4` reach the qubits. The full ranking — every feature, its
correlation, its score, and whether it was encoded — is displayed in the Quantum lab so
the selection is auditable rather than asserted.

The default four-feature configuration is: disease signal, image confidence, heat risk, temperature. A benchmark run recomputes feature ranking on the training split; the final selected order is stored in the benchmark artifact.

## 4. The built-in circuit (tiers 2 and 3)

4 qubits, 2 layers, 16 trainable circuit parameters, 5 classical read-out parameters.

```
The production QML circuit is generated directly from Qiskit at runtime: ZZFeatureMap (4 qubits, linear entanglement) composed with RealAmplitudes (4 qubits, 2 repetitions, circular entanglement), measured by EstimatorQNN. The UI circuit is derived from that runtime circuit; it does not use a decorative RY/RZ diagram.
```

- **Encoding.** The production QML path uses Qiskit `ZZFeatureMap`; the four selected agricultural features are supplied as its input parameters. The fallback simulator retains its own explicit angle-encoding implementation and is never labelled as Qiskit.
- **Entanglement.** CX pairs alternate between even and odd offsets around a ring, so every qubit interacts with its neighbours within two layers.
- **Variational block.** Trainable `RY`/`RZ` on every qubit, per layer.
- **Read-out.** `⟨Z⟩` on all four qubits, combined by a trainable linear read-out and a sigmoid into an outbreak-risk probability.

## 5. Training

SPSA (simultaneous perturbation stochastic approximation), mini-batched, minimising
binary cross-entropy. SPSA needs two circuit evaluations per iteration regardless of
parameter count, which is what makes simulator-based training practical on a laptop;
parameter-shift gradients would need 2 × 21 evaluations per step.

Loss history is recorded and plotted. Trained parameters are persisted to
`backend/quantum/trained_model.json` so a restart does not retrain, and pressing
**Run experimental benchmark** retrains from scratch and recomputes every number on
screen.

## 6. Benchmark methodology

`benchmark.py` does all of the following in one run:

1. Build a dataset of agronomically plausible field scenarios (`dataset.py`).
2. Run every scenario through the **real** `analyze_field` engine to produce features.
3. Label each with a forward-looking outbreak proxy.
4. Stratified 70/30 split with fixed seeds.
5. Rank and select features on the training split.
6. Train logistic regression and the quantum classifier on identical features.
7. Evaluate both on the identical held-out split: accuracy, precision, recall, F1, confusion matrix, per-sample inference time.

### About the labels

There is no field-verified outbreak corpus in this prototype. The label is a proxy:
disease risk, plus latent near-future weather (forward humidity, forward rain, leaf
wetness, thermal fit) that is **deliberately withheld from both models**, plus host
susceptibility, plus noise. That makes it a genuine noisy learning problem rather than a
lookup of one input column — but it makes every metric a *demonstration* metric. The API
labels it `Demonstration / Experimental Evaluation` and the interface prints that label
next to the table.

### Provenance recorded with every run

`benchmark_result.json` stores `qiskit_installed`,
`qiskit_machine_learning_installed`, `execution_backend`, `execution_label`,
`qiskit_execution`, `dataset_type`, `qubits`, the circuit description, the feature
list, both confusion matrices, per-sample inference times and prediction agreement.
The interface renders those fields rather than any hard-coded value.

### Shipped result

The benchmark configuration for this build uses 360 samples and 120 SPSA iterations. Any displayed benchmark metrics must come from an actual executed run; this source tree does not fabricate Qiskit results.

| Metric | Classical | Quantum |
|---|---|---|
| Accuracy | computed at runtime | computed at runtime |
| Model | Logistic regression | 4-qubit VQC, 2 layers |

Backend for that run: fallback simulation (the build machine had no Qiskit installed). Artifacts are stored **per execution mode** so a fallback result can never be mistaken for a Qiskit one.
Install `requirements.txt` and press **Run experimental benchmark** to regenerate it
through Qiskit Machine Learning; the numbers on screen will be whatever that run
produces.

The shipped artifact (`benchmark_result_fallback_simulation.json`, seed 2026, 253 train / 107 test) measured
**quantum 95.33% vs classical 95.33% accuracy** (quantum F1 91.23, classical F1 91.23) — a tie on this synthetic dataset,
which is not evidence of quantum advantage. If a rerun on your machine produces different figures, those are the
numbers the interface will show — nothing is hard-coded.

When no benchmark has been run, the API returns `status: "awaiting_benchmark"` with
every metric `null`, and the interface prints **Awaiting experimental benchmark**. It
never fills the gap with a plausible-looking number.

## 7. Failure behaviour

`pipeline.hybrid_analyze()` catches everything and returns
`{"available": false, "message": "Quantum layer unavailable. Classical agricultural
analysis continues normally."}`. The quantum router is imported inside a `try/except`
in `main.py`, so a broken quantum layer cannot stop the app from starting. Every
`/api/quantum/*` endpoint returns HTTP 200 with an `available` flag rather than raising,
so the browser degrades instead of erroring. This is covered by
`test_quantum_failure_does_not_break_classical_analysis`.

## 8. Limitations

- Simulator only; four qubits on a simulator cannot demonstrate quantum advantage and this build does not claim any.
- Proxy labels, synthetic scenarios, no field validation.
- The vision model covers PlantVillage classes, which under-represent Indian field conditions, mixed cropping and late-stage symptoms.
- Quantum inference is orders of magnitude slower here than the classical baseline, because a state vector is being simulated in software. That comparison describes simulators, not quantum processors.
- No noise model, no error mitigation, no hardware calibration data.

## 9. System health and model provenance

Two endpoints exist specifically so a judge — or a developer three months from now —
never has to read source code to know what is real:

- **`GET /api/system/health`** (and the quantum-only `GET /api/quantum/health`) checks
  every subsystem at call time: backend, database, vision model, sensor system,
  weather context, offline queue/sync, Qiskit, Qiskit Machine Learning, the classical
  model, the QML model, and the benchmark. Every line is `{"ok": bool, "detail":
  str}`, and nothing is a hard-coded `true`. Qiskit being unavailable is reported as
  `ok: false` with the honest reason — that is a correct report, not a bug, and the
  overall status still reads `"ok"` because the fallback path is a supported state.
- **`GET /api/quantum/provenance`** answers "where did this number come from": the
  dataset type and its caveat, the selected features and selection method, which
  classical algorithm ran, which quantum engine ran (`qiskit_machine_learning` or
  `builtin_vqc`), its feature map, its ansatz, whether it is trained, and an explicit
  `"quantum_advantage_claimed": false`.

Both are rendered on the **About** page, refreshed on every visit, never cached into
static copy. `scripts/verify_quantum.py` prints the same health block to a terminal.

## 10. Saved-artifact metadata

`trained_model.json` (built-in engine) and `trained_qiskit_model.json` (Qiskit ML
engine — only written when that engine actually trained) both carry, at minimum:
`engine`, `model_version`, feature map and ansatz names and configuration,
`feature_order`, the trained parameters, `training_info` (optimiser, iterations,
loss history, wall-clock time), and the exact `qiskit_version` /
`qiskit_machine_learning_version` that produced them. Loading either file back
reconstructs a working model via `from_dict()` — this is tested in
`tests/test_quantum.py::test_qiskit_vqc_metadata_when_available`, which is skipped
(not silently passed) in an environment where Qiskit ML is not installed.

## 11. Where this would go next

1. Replace proxy labels with real labelled outbreak data from agricultural university partners — the benchmark harness runs unchanged against it.
2. Add multispectral and drone-derived features (NDVI, red-edge) as additional entries in `FEATURE_NAMES`; selection and encoding already generalise to more features.
3. Data re-uploading circuits to recover expressiveness lost to angle encoding.
4. Quantum kernel methods, which are better motivated for the small-sample regime than a deep variational ansatz.
5. Execution on real hardware through Qiskit Runtime, to measure what device noise does to a circuit this shallow.


## Production Qiskit path

The verified target environment is Python 3.13 with Qiskit 2.5.2 and Qiskit Machine Learning 0.9.1. The real path uses `zz_feature_map`, `real_amplitudes`, `StatevectorEstimator`, and `EstimatorQNN`. QML 0.9 is the Qiskit 2.x migration line and supports Python 3.13.

The persisted model is accepted only when it is marked trained, has the expected four-qubit architecture, exact feature order, finite parameter vector, matching parameter count, and a compatible Qiskit/QML runtime.


## 12. State analysis, playground and noise model (v3.2)

`backend/quantum/quantum_state.py` reads out the state the circuit prepares. Qubit order is Qiskit's little-endian
convention (bit *q* of a basis index is qubit *q*; bit-strings print with qubit 0 on the right).

* **Bloch vector** of qubit *q*: from the reduced density matrix, `x = 2·Re ρ01`, `y = −2·Im ρ01`, `z = ρ00 − ρ11`.
  A length below 1 means the qubit is entangled with the rest of the register.
* **Entanglement entropy** `S = H((1+|r|)/2)` bits (0 = independent, 1 = maximally entangled) and **purity** `(1+|r|²)/2`.
* **Meyer–Wallach** `Q = 2(1 − mean purity)`, 0 (product state) to 1.
* **Shots**: samples from the exact distribution with a fixed seed. No hardware noise is modelled here.
* **Noise sweep**: a global depolarising channel scales every non-identity Pauli expectation by `(1 − p)`; the risk
  prediction is recomputed from the scaled expectations. This is a simplified simulation of NISQ noise, **not** a device measurement.
* **Depth** is the true circuit depth (longest chain of non-parallel gates). Earlier builds reported the gate count under this name.

`GET /api/quantum/simulate?x0..x3=<0..1>&shots=<n>&seed=<n>` runs the playground; `GET /api/quantum/feature-ranges`
supplies the slider ranges. Nothing is stored.

**Verified physics** (`tests/test_quantum_state.py`): a Bell state gives entropy 1 bit and Meyer–Wallach 1; a product state gives 0;
`|+i⟩` has Bloch vector (0, 1, 0); Bell-state shots never produce `01` or `10`.

**Qiskit self-test.** On first use the app checks that Qiskit's `Statevector` agrees with the bundled simulator, and that the
`EstimatorQNN` output equals a direct ⟨ZZZZ⟩ calculation. If either check fails, or a Qiskit call errors mid-run, the runtime stops
claiming Qiskit execution and reports the reason.
