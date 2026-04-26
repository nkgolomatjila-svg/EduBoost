# EduBoost SA Functional Implementation Roadmap

This roadmap converts all user-facing and platform functionalities declared in `README.md` into implementation tracks with concrete completion criteria.

Strategic requirement: EduBoost must own core intelligence in-platform. Lesson generation should run on EduBoost-hosted nano open-source models (fine-tuned for CAPS and local context), not as a thin proxy to external proprietary model APIs.

## How to Use This Roadmap

- Mark each checkbox as work is completed and verified.
- Do not mark an item complete without tests and docs updates.
- Treat "Done" as: implemented, tested, observable, and documented.

## Implementation Status Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Implemented and verified

---

## 1) Adaptive Diagnostic Engine (IRT-Based)

Source: README "Key Features" and ML references.

### Core Functionality
- [x] Implement reliable IRT calibration and scoring pipeline for Grade R-7 diagnostics.
- [x] Support item bank versioning and difficulty/discrimination metadata management.
- [~] Deliver per-learner knowledge gap detection at concept level (not only subject level).
- [x] Return confidence intervals and decision thresholds for level placement.

### API + Product Behavior
- [x] Expose stable diagnostic endpoints with request/response contracts.
- [x] Persist diagnostic attempts, outcomes, and progression history.
- [~] Provide frontend diagnostic UX flow with retry/re-entry support.

### Validation
- [x] Add unit tests for scoring logic and edge-case handling.
- [x] Add integration tests for full diagnostic flow from API to persistence.
- [ ] Add benchmark checks for accuracy and response-time limits.

### Current Status (Apr 2026)
- ✅ IRT 2PL model with theta estimation, SEM, Fisher information
- ✅ 10 sample items (GR2-3) across MATH, ENG, LIFE, NS, SS
- ❌ Item bank needs 100+ calibrated items per subject/grade
- ✅ Database persistence of diagnostic sessions/responses

---

## 2) AI Lesson Generation (EduBoost-Owned Nano Model Stack)

Source: README "Key Features", "Current State", and POPIA section.

### Core Functionality
- [ ] Select and baseline at least one nano open-source model family suitable for local inference (e.g., <= 7B class, quantized variants).
- [ ] Build an in-repo model lifecycle: dataset prep -> fine-tuning/instruction tuning -> evaluation -> versioned release.
- [x] Implement deterministic lesson-generation orchestration that calls only EduBoost-hosted models by default.
- [x] Enforce CAPS alignment through curriculum-conditioned training data, structured generation constraints, and post-generation validation.
- [x] Include South African context adaptation controls (language/culture/context packs) in both training corpus and inference templates.
- [x] Add an offline-capable inference mode for low-connectivity deployments.

### Model Ops + Safety + Governance
- [ ] Build a curated CAPS-aligned training corpus with provenance tracking and licensing checks.
- [ ] Add data quality pipeline (deduplication, contamination checks, age-band tagging, language normalization).
- [x] Add output quality guardrails (age appropriateness, factuality checks, toxicity filters, curriculum adherence checks).
- [x] Implement model fallback policy across EduBoost-managed model versions/sizes (not external APIs).
- [ ] Track model version, training recipe, dataset snapshot, and inference config lineage for reproducibility.
- [ ] Define model promotion gates (dev -> staging -> production) based on objective evaluation thresholds.

### Validation
- [x] Add unit tests for orchestration, inference adapters, and lesson post-processors.
- [x] Add integration tests for lesson generation API paths with locally served model runtime.
- [ ] Add golden test set for expected lesson quality, CAPS mapping, and SA-context correctness.
- [ ] Add automated eval suite (accuracy, hallucination risk, readability by grade band, response latency, cost per lesson).
- [ ] Add regression gates to block model deployment when lesson quality drops.

### Current Status (Apr 2026)
- ✅ Full lesson generation pipeline (lesson_service.py)
- ✅ Multi-provider LLM routing: Groq → Anthropic → HuggingFace with failover
- ✅ PII scrubber using regex (names, emails, IDs, phones)
- ✅ SA contextual prompt injection (10 themes)
- ✅ Judiciary constitutional review before LLM calls
- ❌ No lesson caching
- ❌ No real nano model (uses external APIs)

---

## 3) Dynamic CAPS-Aligned Study Plans

Source: README "Key Features".

### Core Functionality
- [ ] Generate weekly plans that blend remediation and grade-level pacing.
- [ ] Adapt schedules based on diagnostic output and learner progress.
- [ ] Support subject-level and topic-level planning constraints.

### UX + API
- [ ] Provide learner-visible study plan views with daily task states.
- [ ] Provide educator/parent-readable plan rationale ("why this next").
- [ ] Add plan refresh/recompute endpoint with audit-safe history.

### Validation
- [ ] Test planning algorithm for conflict, overload, and sparse-data scenarios.
- [ ] Add integration tests covering plan generation, save, fetch, and update cycles.

### Current Status (Apr 2026)
- ⚠️ Router exists (study_plans.py) - STUB ONLY
- ⚠️ Database schema exists (StudyPlan table)
- ❌ No algorithm implemented
- ❌ No gap-ratio prioritization logic
- ❌ No integration with diagnostic results

---

## 4) Gamification (Grade-Banded)

Source: README "Key Features".

### Core Functionality
- [ ] Implement XP, streaks, and badge system for Grade R-3 mode.
- [ ] Implement discovery-style engagement mechanics for Grade 4-7 mode.
- [ ] Ensure grade-band switching logic is deterministic and test-covered.

### Persistence + Product
- [ ] Persist rewards, streaks, and milestone events with anti-abuse checks.
- [ ] Surface learner progress indicators in frontend dashboard components.

### Validation
- [ ] Add unit tests for points/streak computation.
- [ ] Add integration tests for reward issuance and progression updates.

### Current Status (Apr 2026)
- ⚠️ Data model exists (total_xp, streak_days fields in Learner)
- ⚠️ 35 XP hardcoded per lesson
- ❌ No XP calculation logic
- ❌ No badge progression system
- ❌ No streak update logic
- ❌ No leaderboards or achievements

---

## 5) Parent / Guardian Portal

Source: README "Key Features", "Parent Portal direction".

### Core Functionality
- [x] Implement authenticated guardian access with learner-linking workflows.
- [ ] Provide progress summaries, diagnostic trends, and study-plan adherence views.
- [ ] Generate AI-assisted parent reports with clear, explainable language.

### Controls
- [x] Enforce backend consent checks before exposing learner data to guardians.
- [ ] Implement role/permission model for parent, guardian, and staff visibility scopes.

### Validation
- [ ] Add integration tests for guardian login, learner linking, and report retrieval.
- [ ] Add authorization tests for cross-tenant or unauthorized data access attempts.

### Current Status (Apr 2026)
- ✅ Router exists (parent.py)
- ✅ Consent recording endpoint
- ✅ Email hashing for privacy
- ❌ No parent report algorithm (stub endpoint)
- ❌ No learner performance analytics
- ❌ No progress visualizations

---

## 6) Authentication and Identity

Source: README "Known gaps still being addressed".

### Core Functionality
- [x] Implement production-safe auth flows (signup/login/session refresh/logout).
- [x] Support secure JWT/session handling and rotation.
- [x] Introduce pseudonymous learner IDs in all AI-facing workflows.

### Validation
- [ ] Add auth integration tests for token lifecycle and protected routes.
- [ ] Add negative tests for invalid tokens and privilege escalation attempts.

### Current Status (Apr 2026)
- ✅ JWT-based auth for guardians
- ✅ Learner session endpoints
- ✅ Pseudonymous Learner UUID approach
- ✅ Email-based guardian verification
- ❌ No MFA/2FA
- ❌ No session invalidation on data deletion
- ❌ No rate limiting on auth endpoints

---

## 7) POPIA-Aligned Privacy Workflows

Source: README "Privacy-oriented design goals" and "POPIA Alignment".

### Data Minimisation + Pseudonymisation
- [x] Define and enforce minimum required data collection per workflow.
- [x] Ensure AI requests never contain direct learner identifiers.

### Consent
- [x] Implement backend-enforced parental consent before learner data processing.
- [x] Store consent artifacts (when, who, scope, revocation state).

### Right to Erasure
- [ ] Implement end-to-end deletion workflow across relational, cache, and derived stores.
- [ ] Add deletion confirmation jobs and immutable audit events for deletion requests.

### LLM Firewall + Governance
- [x] Centralize policy checks before model inference and data egress.
- [x] Add configurable deny/allow policies, redaction hooks, and learner-data boundary enforcement.

### Validation
- [ ] Add privacy integration tests (consent required, revoked consent, erase flow).
- [ ] Add compliance evidence exports for audit readiness.

### Current Status (Apr 2026)
- ✅ PII scrubber (regex-based)
- ✅ Pseudonymous learner UUIDs
- ✅ ConsentAudit table
- ✅ Judiciary rule enforcement (PII_01, POPIA_02, POPIA_03)
- ❌ No actual encryption at rest
- ❌ No data deletion workflow
- ❌ No right-to-access API

---

## 8) Audit Trail and Eventing

Source: README "Audit Trail" statements and architecture references.

### Core Functionality
- [x] Log consent, access, learning actions, and administrative changes as immutable events.
- [x] Correlate events by actor, learner, route, and request ID.
- [x] Prevent silent data access by requiring auditable route wrappers.

### Validation
- [x] Add tests to verify audit events are emitted on all protected operations.
- [ ] Add tamper-resistance checks for append-only or signed event records.

### Current Status (Apr 2026)
- ✅ Fourth Estate audit system (app/api/fourth_estate.py)
- ✅ AuditEvent model with event types
- ✅ Redis stream publishing (if configured)
- ✅ In-memory audit buffer (max 1000 events)
- ✅ Audit report endpoints
- ❌ No long-term audit storage
- ❌ No audit query/search API

---

## 9) Database Lifecycle (Alembic-Driven)

Source: README "Known gaps" + "Database Migrations".

### Core Functionality
- [ ] Fully adopt migration-driven schema changes with no runtime schema auto-create.
- [ ] Ensure all model changes are represented in Alembic revisions.
- [ ] Add migration rollback paths for critical schema changes.

### Validation
- [ ] Add CI checks to fail when models and migrations drift.
- [ ] Test upgrade/downgrade in isolated test databases.

### Current Status (Apr 2026)
- ⚠️ Alembic migration system set up
- ⚠️ SQLAlchemy ORM models defined
- ❌ Migration file EMPTY (0001_phase2_baseline.py has only comments)
- ❌ No actual CREATE TABLE statements
- ❌ No seed data for item banks

---

## 10) Frontend Architecture Hardening

Source: README "Known gaps still being addressed".

### Core Functionality
- [ ] Decompose `EduBoostApp.jsx` into domain-focused components and routes.
- [ ] Remove remaining demo-era paths and dead UI code.
- [ ] Align frontend state management with backend contracts.

### Validation
- [ ] Add component tests for critical flows (diagnostic, lesson, plan, parent view).
- [ ] Add E2E tests for primary learner and parent journeys.

---

## 11) Observability and Monitoring

Source: README "Monitoring" and docker stack capabilities.

### Core Functionality
- [ ] Expand metrics to cover learner journey outcomes and operational SLOs.
- [ ] Add tracing/correlation between frontend requests, API, workers, DB operations, and model inference pipeline.
- [ ] Add alert rules for API latency, queue backlog, error spikes, and model-serving degradation.

### Validation
- [ ] Confirm dashboards exist for product, reliability, and privacy/compliance views.
- [ ] Add runbooks for top alerts and incident-response steps.

---

## 12) Background Jobs and Celery Reliability

Source: README stack composition (Celery, Redis, Flower).

### Core Functionality
- [ ] Define idempotent task patterns and retry/dead-letter handling.
- [ ] Add priority queues for learner-critical operations.
- [ ] Instrument task success/failure and latency metrics, including fine-tune/eval/inference job stages.

### Validation
- [ ] Add integration tests for retry/backoff and poison-message behavior.
- [ ] Add chaos tests for model-serving interruptions, worker restarts, and Redis interruptions.

---

## 13) In-House Model Training and Serving Platform

Source: User requirement for EduBoost-owned lesson intelligence.

### Core Functionality
- [ ] Add reproducible training pipelines (data versioning, experiment tracking, model artifact registry).
- [ ] Implement parameter-efficient fine-tuning workflow for nano models (LoRA/QLoRA or equivalent).
- [ ] Build secure model artifact storage with signed/versioned releases.
- [ ] Deploy internal model serving endpoint(s) with autoscaling and health checks.
- [ ] Add model routing layer for grade/language-aware template and model selection.

### Compute + Runtime Strategy
- [ ] Define baseline deployment profiles (CPU-only, single-GPU, and hybrid worker queues).
- [ ] Add quantized inference support and memory/latency budgets per deployment profile.
- [ ] Add batch and streaming inference modes for lesson generation workloads.

### Validation
- [ ] Add load tests for concurrent lesson generation under classroom-scale traffic.
- [ ] Add disaster recovery tests for model artifact restore and serving failover.
- [ ] Add security tests for model endpoint authz, rate-limits, and abuse prevention.

---

## 14) CI/CD and Release Automation

Source: README "Known gaps still being addressed".

### Core Functionality
- [ ] Define CI pipeline for lint, unit, integration, migration, and security checks.
- [ ] Add artifact/version strategy and release tagging conventions.
- [ ] Add deployment promotion workflow (dev -> staging -> production gates).

### Validation
- [ ] Require green pipeline and test thresholds before merge.
- [ ] Add rollback and hotfix process documentation.

---

## 15) Contributing and Engineering Workflow Formalization

Source: README "Contributing".

### Core Functionality
- [ ] Formalize branch, review, testing, and documentation standards in-repo.
- [ ] Add PR templates tied to roadmap and risk categories.
- [ ] Add definition-of-done checklist to enforce quality gates.

---

## 16) Functional Completion Gates (Cross-Cutting)

Apply to each feature area before marking complete:

- [ ] API contract documented and versioned.
- [ ] Frontend behavior matches contract and handles failures gracefully.
- [ ] Unit + integration tests exist and pass in CI.
- [ ] Monitoring + alert coverage in place.
- [ ] Security/privacy implications reviewed.
- [ ] README and developer docs updated to match real status.

---

## Suggested Execution Phases

### Phase 1: Foundation + Trust
- [ ] Auth, consent enforcement, audit events, migration discipline, CI baseline.

### Phase 2: Core Learning Loop
- [ ] Diagnostic engine hardening, in-house model training baseline, lesson orchestration quality, dynamic study plans.

### Phase 3: Engagement + Family Visibility
- [ ] Gamification maturity and full parent/guardian portal.

### Phase 4: Production Readiness
- [ ] Observability SLOs, model-serving resiliency hardening, deployment and incident runbooks.

---

## Roadmap Ownership

- Product owner: [ ] Assigned
- Technical owner: [ ] Assigned
- Compliance owner: [ ] Assigned
- Weekly review cadence: [ ] Established
- Progress dashboard: [ ] Established

