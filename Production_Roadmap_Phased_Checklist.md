# EduBoost SA Production Roadmap Phased Checklist

This document groups the production roadmap into phased execution. The goal is to turn the full roadmap into a practical delivery plan.

## Phase Definitions

- **Phase 0**: truth, safety, and critical unblockers
- **Phase 1**: core production correctness
- **Phase 2**: operational readiness and delivery confidence
- **Phase 3**: product hardening, scale, and quality optimization

---

## Phase 0 — Truth, Safety, and Critical Unblockers

This phase removes unsafe shortcuts, aligns documentation with reality, and closes the most immediate launch blockers.

### Architecture and repo truth

- [ ] Define the single authoritative target architecture for production.
- [ ] Document the approved runtime components: frontend, API, Postgres, Redis, Celery workers, monitoring, and external AI providers.
- [ ] Decide which infrastructure path is primary: Docker, Kubernetes, Bicep, or Supabase-backed hybrid.
- [ ] Remove or rewrite README sections that describe non-existent folders or unsupported deployment flows.
- [ ] Delete dead or duplicate backend modules that no longer belong to the active architecture.
- [ ] Standardize one approved path for lesson generation.
- [ ] Standardize one approved path for study plan generation.
- [ ] Standardize one approved path for parent report generation.

### Immediate backend and frontend safety

- [ ] Remove all browser-direct AI provider calls.
- [ ] Route all AI interactions through backend endpoints only.
- [ ] Create a centralized frontend API client.
- [ ] Fix guardian authentication and authorization.
- [ ] Verify guardian identity before issuing guardian JWTs.
- [ ] Verify guardian-to-learner relationship before granting access.
- [ ] Move all privacy-sensitive enforcement from UI messaging into backend logic.
- [ ] Ensure every regulated workflow passes through orchestration, validation, audit, and privacy controls.

### Config and secrets

- [ ] Remove insecure secret defaults from configuration.
- [ ] Make production startup fail when required secrets are missing.
- [ ] Create separate config profiles for local, test, staging, and production.
- [ ] Move secrets into a managed secret store for production.
- [ ] Add secret scanning to CI.

### Immediate correctness fixes

- [ ] Remove runtime DB auto-create from production path.
- [ ] Add strict schemas and validation to all critical endpoints.
- [ ] Audit every route for missing request and response schemas.
- [ ] Add strict Pydantic models to every route.
- [ ] Reject unknown input fields for sensitive endpoints.
- [ ] Validate LLM JSON against Pydantic models before downstream use.
- [ ] Add business-rule validation for grade, subject, language, and mastery values.

### Immediate documentation and maintainability

- [ ] Update the README to stop overstating current production readiness.
- [ ] Update `README.md` to reflect the actual repo state.
- [ ] Document known limitations and unsupported flows honestly.
- [ ] Break `EduBoostApp.jsx` into smaller feature modules.
- [ ] Break up `EduBoostApp.jsx`.
- [ ] Create separate components for onboarding, dashboard, diagnostics, lessons, study plan, badges, and parent portal.
- [ ] Separate mock/demo data from production logic.

### Phase 0 exit criteria

- [ ] No browser code calls external AI providers directly.
- [ ] Guardian auth is enforced server-side.
- [ ] Critical endpoints use strict schemas.
- [ ] README and repo structure tell the truth.
- [ ] The most dangerous shortcuts have been removed.

---

## Phase 1 — Core Production Correctness

This phase establishes reliable backend behavior, privacy enforcement, durable persistence, and modular frontend foundations.

### Backend correctness and architecture enforcement

- [ ] Separate code into clear layers: routers, schemas, services, adapters, persistence, policy/compliance.
- [ ] Define which workflows are synchronous and which must run asynchronously.
- [ ] Identify all domain events that require audit logging.
- [ ] Create an architecture decision record for major technical choices.
- [ ] Add a dependency map showing which modules are production-critical.
- [ ] Standardize API error responses.
- [ ] Add API versioning rules and document them.
- [ ] Use Alembic as the only database schema migration path.
- [ ] Create rollback instructions for failed migrations.
- [ ] Replace blocking SDK usage in async request paths.
- [ ] Review all external I/O for correct timeout behavior.
- [ ] Add retry policies with bounded backoff for external AI calls.
- [ ] Add circuit breakers around provider failures.
- [ ] Add idempotency protection for retry-prone write operations.
- [ ] Persist generated lessons with durable IDs.
- [ ] Persist generated study plans where product history is required.
- [ ] Persist parent reports where product history is required.
- [ ] Define cache versus database ownership for every generated artifact.
- [ ] Add structured logging conventions across backend modules.
- [ ] Add correlation/request IDs to logs.
- [ ] Introduce rate limiting on high-cost and abuse-prone endpoints.
- [ ] Add graceful degradation behavior for provider outages.
- [ ] Review all routers for consistency in naming, status codes, and error handling.
- [ ] Remove stale experimental logic from the request path.
- [ ] Add repository-level coding standards for backend modules.

### Privacy and security core

- [ ] Add role-based authorization rules.
- [ ] Add context-aware authorization for sensitive endpoints.
- [ ] Define token expiry, rotation, and revocation behavior.
- [ ] Centralize PII detection patterns in one module.
- [ ] Reconcile inconsistencies in current scrubber rules.
- [ ] Add tests to ensure learner IDs never reach AI providers.
- [ ] Add tests to ensure guardian email never reaches AI providers.
- [ ] Review all logs for accidental PII leakage.
- [ ] Replace weak identifier hashing patterns with keyed hashing where required.
- [ ] Define encryption key rotation procedures.
- [ ] Harden CORS policy for production.
- [ ] Add secure response headers where applicable.
- [ ] Review CSRF exposure for auth/session flows.
- [ ] Add monitoring for authentication failures and suspicious access.
- [ ] Define and implement right-to-erasure across database, cache, logs, and analytics.
- [ ] Track deletion requests through a verifiable lifecycle.
- [ ] Define backup retention interactions with deletion policy.
- [ ] Add threat modeling for learner, guardian, AI-provider, and admin attack surfaces.

### Frontend foundations

- [ ] Move inline style definitions into a maintainable styling system.
- [ ] Define a frontend state management strategy.
- [ ] Separate server state from local UI state.
- [ ] Standardize loading states across all screens.
- [ ] Standardize error states across all screens.
- [ ] Standardize retry behavior for failed API calls.
- [ ] Add proper empty states where data may not yet exist.
- [ ] Reduce oversized component responsibilities.
- [ ] Introduce reusable UI primitives for buttons, cards, badges, banners, and forms.
- [ ] Review local storage/session storage usage for sensitive data exposure.
- [ ] Ensure guardian-specific flows are clearly separated from learner flows.
- [ ] Add frontend error telemetry for critical failures.

### Phase 1 exit criteria

- [ ] DB lifecycle is migration-driven.
- [ ] Sensitive workflows are audited and validated.
- [ ] Generated artifacts have durable persistence rules.
- [ ] Core privacy controls are enforced in code.
- [ ] Frontend architecture is modular enough to continue safely.

---

## Phase 2 — Operational Readiness and Delivery Confidence

This phase makes the platform deployable, observable, testable, and recoverable.

### CI/CD and release engineering

- [ ] Define local, CI, staging, and production environments.
- [ ] Define branch protections and merge requirements.
- [ ] Define the release promotion flow from staging to production.
- [ ] Standardize Dockerfiles for lean runtime images.
- [ ] Review health checks for actual readiness, not just liveness.
- [ ] Add resource requests and limits for production deployments.
- [ ] Decide whether Kubernetes manifests are actively supported.
- [ ] Align deployment manifests with actual production architecture.
- [ ] Add CI jobs for linting.
- [ ] Add CI jobs for type checks where applicable.
- [ ] Add CI jobs for backend unit tests.
- [ ] Add CI jobs for frontend tests.
- [ ] Add CI jobs for integration tests.
- [ ] Add CI jobs for build verification.
- [ ] Add CI jobs for migration checks.
- [ ] Add CI jobs for security scans.
- [ ] Add CI jobs for container builds.
- [ ] Add release automation.
- [ ] Add rollback automation or a documented rollback playbook.
- [ ] Add CI quality gates for tests, builds, and security scans.

### Observability and reliability

- [ ] Define logs, metrics, and traces that matter for operations.
- [ ] Add learner-journey metrics such as lesson generation success rate.
- [ ] Add diagnostic completion metrics.
- [ ] Add consent completion metrics.
- [ ] Add parent report generation latency metrics.
- [ ] Add alerting thresholds tied to SLOs.
- [ ] Implement backup automation for Postgres.
- [ ] Define Redis durability expectations.
- [ ] Test restore procedures regularly.
- [ ] Add queue monitoring for Celery.
- [ ] Add dead-letter or failure visibility for async tasks.
- [ ] Add incident severity definitions.
- [ ] Create incident response runbooks.
- [ ] Estimate model-provider cost per core workflow.
- [ ] Add cost controls through caching, quotas, or fallback policies.
- [ ] Define scaling thresholds for API, DB, and worker services.
- [ ] Define service-level objectives for latency, uptime, and recovery.

### Test and QA hardening

- [ ] Expand unit tests for auth flows.
- [ ] Expand unit tests for consent flows.
- [ ] Expand unit tests for deletion flows.
- [ ] Expand unit tests for orchestration logic.
- [ ] Expand unit tests for PII scrubber logic.
- [ ] Expand unit tests for provider fallback logic.
- [ ] Expand unit tests for schema validation failures.
- [ ] Expand integration tests for lesson generation.
- [ ] Add integration tests for guardian login and authorization.
- [ ] Add integration tests for consent capture and audit logging.
- [ ] Add integration tests for deletion requests.
- [ ] Add integration tests for study plan generation.
- [ ] Add integration tests for parent report generation.
- [ ] Add contract tests between frontend and backend APIs.
- [ ] Add contract tests for AI provider response parsing.
- [ ] Add end-to-end tests for learner onboarding.
- [ ] Add end-to-end tests for guardian consent.
- [ ] Add end-to-end tests for diagnostic sessions.
- [ ] Add end-to-end tests for lesson completion.
- [ ] Add end-to-end tests for study plan viewing.
- [ ] Add end-to-end tests for parent portal access.
- [ ] Add end-to-end tests for data deletion requests.
- [ ] Add accessibility testing in CI.
- [ ] Add load tests for high-cost endpoints.
- [ ] Add concurrency tests for async API safety.
- [ ] Add chaos testing for provider outages.
- [ ] Add chaos testing for Redis failures.
- [ ] Add migration safety tests.
- [ ] Create deterministic synthetic learner datasets for testing.
- [ ] Define coverage thresholds for critical modules.
- [ ] Make passing quality gates mandatory before merge.

### Documentation and runbooks

- [ ] Add `CONTRIBUTING.md`.
- [ ] Add engineering setup documentation for backend and frontend.
- [ ] Add architecture documentation with diagrams.
- [ ] Add deployment documentation for the supported environment.
- [ ] Add rollback documentation.
- [ ] Add incident response runbooks.
- [ ] Add database backup and restore runbooks.
- [ ] Add provider-outage handling runbooks.
- [ ] Add deletion-request operational procedures.
- [ ] Add coding standards documentation.
- [ ] Add ownership mapping for major modules.
- [ ] Add dependency maps for critical workflows.
- [ ] Define release checklist documentation.
- [ ] Define launch readiness checklist documentation.

### Phase 2 exit criteria

- [ ] Deployments are automated and gated.
- [ ] The platform is observable and alertable.
- [ ] Restore and incident procedures are documented and tested.
- [ ] Critical user journeys have automated coverage.

---

## Phase 3 — Product Hardening, Scale, and Quality Optimization

This phase improves accessibility, multilingual readiness, AI governance, usability, and scale discipline.

### Data and AI governance

- [ ] Move hardcoded prompts into versioned template files.
- [ ] Track prompt versions in storage or metadata.
- [ ] Define a review process for prompt changes.
- [ ] Validate every AI output against strict schemas.
- [ ] Reject or quarantine invalid AI output.
- [ ] Track provider used, prompt version, and output validation status for each generation.
- [ ] Define provider fallback order and rules.
- [ ] Measure fallback frequency.
- [ ] Measure output schema failure rates.
- [ ] Measure AI response latency per provider.
- [ ] Measure AI cost per generation path.
- [ ] Add educator review workflows for sample generated lessons.
- [ ] Add quality scoring for CAPS alignment.
- [ ] Add quality scoring for age-appropriate language.
- [ ] Add quality scoring for multilingual output quality.
- [ ] Define release criteria for prompt changes.
- [ ] Add AI content incident handling for low-quality or unsafe outputs.
- [ ] Create a process for evaluating RLHF data quality before using it.
- [ ] Ensure all AI telemetry remains privacy-safe.

### Product and accessibility maturity

- [ ] Audit the true state of multilingual support.
- [ ] Separate UI translation support from lesson-language support.
- [ ] Create a rollout plan for additional official languages.
- [ ] Validate curriculum terminology quality per language.
- [ ] Add offline-friendly caching for recent lessons.
- [ ] Add offline-friendly caching for current study plans.
- [ ] Define sync behavior after reconnect.
- [ ] Optimize large payload sizes for low-bandwidth users.
- [ ] Add voice support planning for early-grade learners if this remains a product goal.
- [ ] Validate age-appropriate reading complexity by grade band.
- [ ] Test product flows on lower-end Android devices.
- [ ] Make diagnostic sessions stateful instead of simulated where needed.
- [ ] Ensure guardian controls are functional, not just presentational.
- [ ] Add downloadable learner data exports if product requirements require it.
- [ ] Add request status visibility for deletion and privacy actions.
- [ ] Validate usability with real target-user scenarios.
- [ ] Add product analytics that do not compromise learner privacy.

### Frontend and UX completion

- [ ] Make learner sessions resumable after refresh where appropriate.
- [ ] Make diagnostic sessions resumable.
- [ ] Persist lesson progress if product requirements demand it.
- [ ] Add responsive behavior for smaller mobile devices.
- [ ] Add keyboard navigation across all core flows.
- [ ] Improve screen-reader semantics.
- [ ] Ensure color contrast meets accessibility standards.
- [ ] Add focus states for interactive elements.
- [ ] Add route-level tests for major app flows.

### Security and launch assurance

- [ ] Run dependency vulnerability scanning.
- [ ] Run container image scanning.
- [ ] Plan and perform penetration testing before launch.

### Final implementation-order checks

- [ ] First, eliminate architecture drift and remove unsafe shortcuts.
- [ ] Second, enforce backend correctness: auth, schemas, migrations, async safety, provider controls.
- [ ] Third, modularize the frontend and remove demo-style patterns.
- [ ] Fourth, complete privacy, deletion, and audit guarantees.
- [ ] Fifth, productionize CI/CD, monitoring, backup, and restore.
- [ ] Sixth, deepen automated coverage for all critical user journeys.
- [ ] Seventh, harden AI governance, output quality, and educational correctness.
- [ ] Eighth, expand multilingual, offline, and accessibility capabilities in a controlled way.

### Phase 3 exit criteria

- [ ] The product works under realistic learner and guardian conditions.
- [ ] AI behavior is governed, measurable, and reviewable.
- [ ] Accessibility and low-connectivity support are materially improved.
- [ ] Launch confidence is supported by testing, operations, and quality controls.
