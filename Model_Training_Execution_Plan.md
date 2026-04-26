# Model Training Execution Plan

This plan translates the roadmap requirement into an executable schedule for building EduBoost-owned lesson generation with nano open-source models.

## Planning Assumptions

- Target model class: nano/small open-source models suitable for local or modest GPU serving.
- Initial use case: CAPS-aligned lesson generation for Grade R-7.
- Delivery style: iterative, measurable, with gated promotion to production.

## Team Roles (Suggested)

- **ML Lead**: training strategy, evaluation design, model promotion decisions.
- **Data Engineer**: dataset ingestion, cleaning, versioning, quality checks.
- **Backend Engineer**: training/inference pipelines, API integration, orchestration.
- **MLOps Engineer**: artifact registry, serving infrastructure, observability.
- **Curriculum Reviewer**: CAPS alignment and pedagogical quality checks.

---

## 10-Week Practical Schedule

## Week 1 - Scope, Baseline, and Tooling Setup

### Goals
- Finalize first release scope (subjects, grades, languages).
- Establish reproducible experimentation foundations.

### Tasks
- [ ] Define V1 target matrix: grade bands, subjects, lesson formats, output length.
- [ ] Select 2-3 candidate nano models for benchmarking.
- [ ] Set up experiment tracking (runs, metrics, artifacts).
- [ ] Set up dataset versioning conventions and storage layout.
- [ ] Define initial eval rubric (CAPS coverage, factuality, readability, safety).

### Deliverables
- [ ] Written model-selection criteria.
- [ ] Benchmark harness scaffold.
- [ ] Eval rubric v1 approved by curriculum reviewer.

### Exit Criteria
- [ ] Team can run one baseline inference benchmark end to end.

---

## Week 2 - Data Pipeline and Corpus Foundation

### Goals
- Build trustworthy CAPS-aligned training/eval corpus pipeline.

### Tasks
- [ ] Ingest raw curriculum-aligned sources and internal content.
- [ ] Apply licensing/provenance checks and source attribution tagging.
- [ ] Implement cleaning: deduplication, normalization, language checks.
- [ ] Add schema for examples (grade, subject, topic, objective, difficulty, locale tags).
- [ ] Split datasets into train/validation/test and freeze snapshot v0.1.

### Deliverables
- [ ] Dataset pipeline scripts.
- [ ] Dataset card (sources, size, known limitations, exclusions).
- [ ] Frozen dataset snapshot v0.1.

### Exit Criteria
- [ ] Re-running pipeline from scratch yields same validated dataset snapshot.

---

## Week 3 - Baseline Evaluation of Candidate Models

### Goals
- Select the best starting model using objective evidence.

### Tasks
- [ ] Run zero-shot and prompted baseline tests on candidate models.
- [ ] Measure latency/cost/memory under expected traffic profile.
- [ ] Score quality with eval rubric and error taxonomy.
- [ ] Select primary and backup model for fine-tuning.

### Deliverables
- [ ] Baseline comparison report.
- [ ] Model choice decision log with trade-offs.

### Exit Criteria
- [ ] Primary baseline model approved for tuning.

---

## Week 4 - Fine-Tuning Pipeline (PEFT) and First Training Run

### Goals
- Produce first tuned checkpoint using parameter-efficient methods.

### Tasks
- [ ] Implement PEFT pipeline (LoRA/QLoRA or equivalent).
- [ ] Configure reproducible training job spec (seeds, params, dataset refs).
- [ ] Train first tuned checkpoint (v0.2).
- [ ] Capture training metadata and push artifacts to registry.

### Deliverables
- [ ] Training pipeline scripts/jobs.
- [ ] Tuned model checkpoint v0.2 + metadata.
- [ ] Training run report (loss curves, runtime, resource profile).

### Exit Criteria
- [ ] At least one reproducible training run completes successfully.

---

## Week 5 - Quality, Safety, and CAPS Constraint Layer

### Goals
- Raise lesson quality with curriculum and safety enforcement.

### Tasks
- [ ] Add structured generation template with CAPS constraints.
- [ ] Add post-generation validators (format, objective alignment, banned content).
- [ ] Add safety filters (age appropriateness, toxicity, harmful advice checks).
- [ ] Evaluate tuned model vs baseline on full rubric.

### Deliverables
- [ ] Constraint and validation modules in inference pipeline.
- [ ] Eval report comparing baseline vs tuned model.

### Exit Criteria
- [ ] Tuned model meets minimum quality thresholds and safety gates.

---

## Week 6 - Backend Integration and Contract Stabilization

### Goals
- Integrate local model serving into EduBoost API flow.

### Tasks
- [ ] Add internal lesson-generation service adapter for local model runtime.
- [ ] Define stable API contracts for lesson generation requests/responses.
- [ ] Add request tracing IDs and inference metadata logging.
- [ ] Implement deterministic fallback to smaller local model version.

### Deliverables
- [ ] Working API integration with local model endpoint.
- [ ] Contract docs with examples and error handling.

### Exit Criteria
- [ ] Lesson endpoint runs fully without external model APIs.

---

## Week 7 - Performance and Reliability Hardening

### Goals
- Meet practical latency and reliability targets.

### Tasks
- [ ] Apply quantization and runtime optimization.
- [ ] Add queueing/retry strategy for inference spikes.
- [ ] Run load tests for classroom-scale concurrent generation.
- [ ] Tune autoscaling and resource limits for model-serving pods/services.

### Deliverables
- [ ] Performance profile report (p50/p95 latency, throughput, memory).
- [ ] Reliability report under degraded conditions.

### Exit Criteria
- [ ] Service stays within agreed SLO targets in load tests.

---

## Week 8 - Pilot Release and Human-in-the-Loop Review

### Goals
- Validate with real internal users before broader rollout.

### Tasks
- [ ] Launch pilot to limited grade/subject slice.
- [ ] Add educator/curriculum review workflow for generated lessons.
- [ ] Collect failure cases and user feedback for retraining backlog.
- [ ] Patch critical issues and retrain if required.

### Deliverables
- [ ] Pilot feedback report.
- [ ] Prioritized model improvement backlog.

### Exit Criteria
- [ ] Pilot quality acceptance threshold reached.

---

## Week 9 - Compliance, Auditability, and Security Controls

### Goals
- Ensure privacy and governance readiness.

### Tasks
- [ ] Verify pseudonymization in model-bound data paths.
- [ ] Validate consent gates before lesson generation.
- [ ] Add audit logging for data access and inference actions.
- [ ] Execute security tests (authz, rate limiting, abuse controls).

### Deliverables
- [ ] Compliance verification checklist.
- [ ] Security and audit test evidence.

### Exit Criteria
- [ ] Compliance/security gates pass for production candidate.

---

## Week 10 - Production Promotion and Operational Readiness

### Goals
- Promote model stack to production with safe rollout controls.

### Tasks
- [ ] Finalize model release candidate and sign artifact.
- [ ] Deploy with canary strategy and rollback hooks.
- [ ] Publish runbooks (incidents, regression response, retraining triggers).
- [ ] Set weekly model health and drift review cadence.

### Deliverables
- [ ] Production model release `v1.0`.
- [ ] Runbook package and monitoring dashboards.

### Exit Criteria
- [ ] Stable production operation with active monitoring and rollback readiness.

---

## Continuous Workstreams (Run Every Week)

- [ ] Data quality monitoring and contamination scanning.
- [ ] Prompt/template and lesson-format regression tests.
- [ ] Safety red-team checks on new model versions.
- [ ] Cost/performance tracking vs SLO and budget.
- [ ] Documentation updates for each release candidate.

---

## Initial KPIs and Gates

## Quality KPIs
- [ ] CAPS objective match rate >= 90% on evaluation set.
- [ ] Curriculum reviewer acceptance >= 85% on sampled outputs.
- [ ] Hallucination-critical error rate <= defined threshold (set in Week 1).

## Performance KPIs
- [ ] Lesson generation p95 latency target met (define by deployment profile).
- [ ] Error rate below operational threshold under expected concurrency.

## Safety and Compliance KPIs
- [ ] 100% consent-gated generation for protected learner profiles.
- [ ] 100% auditable inference events for production traffic samples.

---

## Risks and Mitigations

- **Data quality risk**: weak or noisy corpus degrades model output.
  - Mitigation: stricter data gates, human review, iterative curation.
- **Compute bottlenecks**: training/inference too slow or expensive.
  - Mitigation: quantization, PEFT, model-size tiering, queueing.
- **Curriculum mismatch**: generated lessons drift from CAPS objectives.
  - Mitigation: curriculum-conditioned training + hard validation checks.
- **Operational regressions**: new model versions reduce quality.
  - Mitigation: golden tests, canary rollout, mandatory rollback path.

---

## Definition of Done for V1

- [ ] EduBoost lesson generation runs on in-house hosted nano model stack.
- [ ] External proprietary API dependency is not required for core lesson flow.
- [ ] Model training and release process is reproducible and documented.
- [ ] Quality, safety, performance, and compliance gates pass in CI and staging.
- [ ] Production runbooks and monitoring are active and tested.

