# AstraNex — KshetraSaarthi
## Presentation-ready release checklist · v2.4.0

### 1. What this build demonstrates

AstraNex is an agricultural early-warning decision-support prototype. It combines crop/context observations, sensor signals and weather context into agricultural features, then runs a classical baseline alongside an experimental quantum ML classifier.

The prototype produces an **early-warning level**, supporting evidence and a **scouting-oriented action**. It is designed for farmer-facing workflows and institutional views such as RBKs, agriculture departments and insurers.

### 2. What to demonstrate live

| Screen | Demonstrate | Presenter message |
|---|---|---|
| Home | End-to-end flow | “We turn multiple agricultural signals into an early-warning workflow.” |
| Intelligence | Sensor/weather/context fusion | “Signals are combined before the model decision.” |
| Field scan | A scan and result | “This is screening and decision support, not a confirmed diagnosis.” |
| Quantum lab | Circuit + encoded features | “Four selected features are encoded into a four-qubit experimental classifier.” |
| Early warnings | Warning/action | “The output is designed to trigger earlier scouting and confirmation.” |
| Analytics | Stored trends | “These charts use observations available on this device; they do not imply national deployment.” |
| Research | Methodology | “The quantum path is experimental and benchmarked against a classical baseline.” |
| About | Runtime/provenance | “The UI reports exactly which runtime executed the circuit.” |

### 3. Claims that are supported

- Hybrid classical + experimental quantum ML architecture.
- Four-qubit variational quantum classifier.
- Classical logistic-regression baseline on the same selected features/split.
- Three transparent quantum execution tiers: Qiskit ML, Qiskit Statevector, or bundled fallback simulation.
- Offline-first scan queue and duplicate-safe synchronization.
- Image quality validation and optional ONNX vision inference when the runtime and model weights are installed.
- Synthetic demonstration data for benchmark/training when field-labelled data are unavailable.

### 4. Claims deliberately not made

- No quantum advantage is claimed.
- No quantum hardware is used.
- No field validation is claimed.
- No validated outbreak forecasting is claimed.
- No real multispectral/drone processing is included in this release.
- No pesticide product is prescribed.
- No automated treatment or irrigation hardware actuation occurs.
- No insurance or financial recommendation is generated.

### 5. If the audience asks “Is it really quantum?”

Answer:

> “The architecture contains a real four-qubit variational circuit. When Qiskit Machine Learning is installed, the preferred path is Qiskit Machine Learning with ZZFeatureMap and RealAmplitudes on a local simulator. In environments without Qiskit, the application uses a bundled simulator and explicitly labels it as fallback simulation. We do not present the fallback as Qiskit execution or claim quantum advantage.”

### 6. If the audience asks about multispectral/drone imagery

Answer:

> “The data architecture is designed to accept imagery-derived agricultural features, but this presentation build does not claim to process real multispectral or drone imagery. That is an integration stage requiring the appropriate data pipeline and validation.”

### 7. If the audience asks about accuracy

Use the live Quantum Lab benchmark and show its provenance. Explain that demonstration labels are synthetic/forward-weather proxy labels and are **not field-validated ground truth**. Do not generalize demo metrics to real farms.

### 8. Pre-demo commands

```bash
./run_presentation.sh
```

Optional verification:

```bash
python scripts/verify_quantum.py
pytest -q
python -m compileall -q backend scripts
```

### 9. Release hygiene

The final ZIP should contain source, tests, documentation, frontend assets, demo/presentation instructions and the legacy interface. Runtime-generated databases, uploads, caches and Python bytecode should not be included.
