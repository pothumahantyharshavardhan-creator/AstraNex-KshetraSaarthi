# AstraNex KshetraSaarthi — Full Code Audit & Upgrade v2.4

## Audit scope

Reviewed the FastAPI backend, SQLite persistence layer, hybrid quantum/classical pipeline, image upload/inference path, offline synchronization path, API schemas, frontend JavaScript modules, test suite, and readiness/verification scripts.

## Findings

### High priority — fixed
1. **Duplicate alert creation on idempotent requests.**
   A repeated `client_event_id` correctly reused an observation ID but still created a second alert. The storage path now detects an existing event before alert creation.
2. **Invalid image bytes could pass MIME validation.**
   The image endpoint trusted the multipart content type before saving. Pillow verification now happens before persistence.
3. **Invalid foreign keys could become server errors.**
   Unknown `field_id` / `observation_id` values are now validated and return a client-facing 422 response.
4. **Offline sync did not fully mirror live analysis.**
   Synced observations now pass through the common result-storage path, including warning generation and idempotency.

### Medium priority — fixed
5. **Multimodal latency telemetry mixed fusion and validation time.** Corrected.
6. **Background training had an unlocked race at startup.** Corrected with the shared training lock.
7. **Finite-number validation was implicit rather than explicit.** Added schema validators.
8. **Sync request size was unbounded.** Capped at 60 observations per request.
9. **Dead conditional in quantum feature endpoint.** Removed.

### Observed but intentionally not overstated
10. **Multispectral/drone processing is not implemented yet.** The current system uses RGB image screening/ONNX vision plus sensor/weather context. It should not claim real multispectral/drone inference until those data paths are added and validated.
11. **The quantum benchmark is experimental.** Its dataset is synthetic and its labels are a forward-weather proxy, not field-verified outbreak ground truth.
12. **Qiskit hardware execution is not present.** Runtime reporting explicitly distinguishes Qiskit ML, Qiskit statevector and the bundled fallback simulator.
13. **PlantVillage is a closed-world dataset.** Unsupported crops should remain in verification/context-monitoring mode rather than being silently diagnosed.

## Upgrade priorities for the next phase

1. Add a real multispectral ingestion contract (band metadata, geospatial reference, acquisition timestamp, cloud/quality flags).
2. Add temporal field-level features rather than relying on single observations.
3. Add validated pest/outbreak labels from agricultural departments/RBKs or other governed field sources.
4. Add calibration and threshold evaluation on a held-out, field-collected dataset.
5. Add authentication/authorisation before institutional deployment.
6. Move uploaded imagery and high-volume telemetry out of local SQLite/filesystem for production scale.
7. Add rate limiting and audit logging to public-facing deployments.
8. Validate the pinned Qiskit ML and ONNX runtime paths in a networked environment with their actual artifacts.

## Verification snapshot

- Python compilation: PASS
- Frontend JavaScript syntax: PASS
- Automated tests: PASS (64 tests)
- Real Qiskit ML execution: not available in this packaging environment
- Real ONNX vision inference: not available in this packaging environment
