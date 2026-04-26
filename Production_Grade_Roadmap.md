# EduBoost SA Production Grade Roadmap

## Purpose

This document defines the work required to move EduBoost SA from a promising MVP/prototype into a truly production-grade platform for real learner traffic. It is structured as an engineering roadmap, not just a feature wishlist. The focus is reliability, safety, maintainability, educational correctness, operational excellence, and regulatory readiness.

The roadmap is organized into the following sections:

- Architecture
- Backend Quality
- Frontend Quality
- Privacy and Security
- Infra and DevOps
- Test Coverage and Quality Assurance
- Data and AI Governance
- Product and Accessibility Readiness
- Documentation and Team Enablement
- Execution Phases and Exit Criteria

---

## Current State Summary

EduBoost SA already has several strong foundations:

- clear product vision and educational purpose
- promising FastAPI backend structure
- an adaptive learning and lesson-generation direction
- local development stack with Docker, Postgres, Redis, Prometheus, and Grafana
- privacy-aware data modeling concepts
- early unit and integration coverage

However, the project is not yet production-grade. The biggest gaps are:

- architecture drift between README claims and actual implementation
- a monolithic frontend implementation acting partly as a demo
- direct browser-to-LLM calls that must be eliminated
- incomplete auth, consent, persistence, and audit controls
- insufficient migration discipline and operational hardening
- limited end-to-end coverage for critical user journeys

---

## 1. Architecture

### Objective

Create a system architecture that is modular, enforceable, observable, and safe under production load.

### Required Work

#### 1.1 Establish the target architecture baseline

- Define the authoritative runtime architecture in one place.
- Standardize service boundaries between frontend, API, async workers, Redis, Postgres, and external AI providers.
- Decide and document which components are production-critical versus optional.
- Align repository structure with the actual architecture.

#### 1.2 Remove architecture drift

- Update the README to reflect the real repo layout.
- Remove references to directories or files that do not exist.
- Remove obsolete or duplicate implementation paths.
- Delete dead draft modules that can confuse maintainers.

#### 1.3 Formalize service boundaries

- Ensure all AI calls go through backend services only.
- Enforce that the frontend never calls model vendors directly.
- Route lesson generation, study plan generation, and parent report generation through a single reviewed orchestration path.
- Ensure privacy, validation, auditing, and rate limiting happen before vendor calls.

#### 1.4 Introduce clear domain layers

Target layers should be:

- routers/controllers
- request/response schemas
- domain services
- infrastructure adapters
- persistence layer
- policy and compliance layer

The code should avoid mixing these concerns in the same module.

#### 1.5 Adopt event-driven boundaries where needed

- Define which workflows must be synchronous versus asynchronous.
- Use Celery for long-running and retryable tasks.
- Emit auditable domain events for consent, lesson generation, report generation, deletion requests, and access to sensitive data.

#### 1.6 Define production non-functional requirements

Document and enforce targets for:

- availability
- response time
- recovery time
- backup and restore
- observability coverage
- data retention
- security posture

### Exit Criteria

Architecture is production-ready when:

- the live implementation matches the documented design
- there is exactly one approved path for each critical workflow
- browser clients cannot bypass backend governance
- async workloads are isolated from request/response traffic

---

## 2. Backend Quality

### Objective

Make the backend predictable, validated, maintainable, and resilient under concurrency and failure.

### Required Work

#### 2.1 Tighten configuration management

- Remove insecure development defaults for secrets.
- Fail fast when required production secrets are missing.
- Separate dev, test, staging, and production configuration profiles.
- Validate environment settings at startup.

#### 2.2 Replace startup schema creation with migrations

- Stop using runtime table auto-creation in production paths.
- Adopt Alembic as the only schema evolution mechanism.
- Add migration checks to CI.
- Define rollback procedures for failed schema deployments.

#### 2.3 Standardize API contracts

- Use strict Pydantic request and response models for every route.
- Reject unknown fields for regulated workflows.
- Return structured errors with consistent schemas.
- Add versioning discipline for API changes.

#### 2.4 Harden orchestration and routing

- Route all regulated operations through orchestration and policy checks.
- Add typed action definitions for every workflow.
- Ensure audit writes occur for all sensitive or learner-affecting actions.
- Remove bypass routes and side-door logic.

#### 2.5 Improve concurrency and async correctness

- Replace blocking SDK usage in async request paths.
- audit all I/O clients for sync/async mismatches.
- ensure retries, timeouts, and cancellation behavior are explicit.
- define per-provider timeout budgets.

#### 2.6 Improve data persistence discipline

- Persist generated lessons with durable IDs.
- Persist study plans and parent reports where product requirements demand history.
- add idempotency where retried requests could create duplicates.
- define cache versus system-of-record responsibilities.

#### 2.7 Strengthen domain validation

- validate lesson JSON against typed schemas before it reaches downstream code.
- validate educational payload shapes for diagnostics, reports, and study plans.
- add explicit business-rule validation for grades, languages, subjects, and learner state.

#### 2.8 Improve dependency hygiene

- deduplicate dependencies in `requirements.txt`.
- pin versions consistently.
- separate runtime and development/test dependencies.
- define dependency update cadence and vulnerability response process.

#### 2.9 Add backend performance protections

- introduce request rate limiting.
- add circuit breakers around external providers.
- apply backpressure and queue limits for expensive workloads.
- cache deterministic or repeatable outputs where appropriate.

### Exit Criteria

Backend is production-ready when:

- all routes have strict contracts
- schema changes are migration-driven only
- blocking calls are removed from async paths
- failures degrade cleanly and predictably
- external provider instability does not cascade into API instability

---

## 3. Frontend Quality

### Objective

Transform the frontend from a monolithic prototype into a maintainable, secure, accessible production application.

### Required Work

#### 3.1 Break up the monolith

- Split `EduBoostApp.jsx` into route-level pages, feature components, hooks, services, and utility modules.
- remove inline mega-style definitions and move to a scalable styling system.
- separate demo data from live application logic.
- create clear ownership boundaries for onboarding, learner dashboard, diagnostics, lessons, plan, badges, and parent portal.

#### 3.2 Remove client-side LLM integration

- delete all direct model-provider calls from the browser.
- ensure the frontend communicates only with approved backend endpoints.
- ensure no secret-bearing or policy-sensitive logic runs in the browser.

#### 3.3 Add frontend architecture standards

- standardize state management strategy.
- define when to use local component state, global state, and server state.
- centralize API client logic.
- centralize error, loading, and retry behavior.

#### 3.4 Improve UX production readiness

- add proper loading states, error states, empty states, and offline states.
- make all core flows recoverable after refresh or interruption.
- ensure parent and learner experiences are separated appropriately.
- support resumable diagnostics and lesson sessions.

#### 3.5 Add design system foundations

- define reusable tokens for color, spacing, typography, border radius, and elevation.
- create shared UI primitives.
- ensure consistency across learner and guardian experiences.
- introduce responsive patterns for low-cost phones and tablets.

#### 3.6 Accessibility hardening

- ensure semantic HTML and keyboard navigation.
- meet WCAG expectations for contrast and focus states.
- add screen-reader support for navigation and lesson content.
- support young learners and multilingual contexts.

#### 3.7 Frontend security and data discipline

- avoid storing sensitive data in unsafe browser storage.
- ensure auth and consent status is sourced from backend truth.
- reduce exposure of internal identifiers.
- review all analytics and logs for accidental PII leakage.

### Exit Criteria

Frontend is production-ready when:

- no direct vendor AI calls exist in browser code
- the codebase is modular and maintainable
- key journeys are resilient and accessible
- UI behavior is consistent across network and device conditions

---

## 4. Privacy and Security

### Objective

Achieve real operational privacy and security controls suitable for learner data and POPIA obligations.

### Required Work

#### 4.1 Enforce server-side-only sensitive workflows

- all consent-sensitive and learner-sensitive workflows must execute through backend policy checks.
- no privacy control may rely only on UI messaging.

#### 4.2 Complete guardian authentication and authorization

- verify guardian identity before issuing JWTs.
- confirm guardian-to-learner relationship before allowing access.
- add token expiry, rotation, revocation, and session invalidation strategy.
- implement role-based and context-aware authorization.

#### 4.3 Harden secret and key management

- remove placeholder production secrets.
- store secrets in managed secret stores, not static files or weak defaults.
- rotate API keys and encryption secrets safely.
- document incident response for key exposure.

#### 4.4 Strengthen PII controls

- centralize PII detection patterns.
- improve scrubber coverage and false-positive handling.
- ensure structured and unstructured payloads are both scrubbed.
- verify learner identifiers and guardian data never reach LLM providers.

#### 4.5 Implement strong cryptographic practices

- replace weak or reversible identifier patterns with keyed hashing where needed.
- review encryption at rest and in transit.
- document key derivation, rotation, storage, and deletion processes.
- ensure audit integrity cannot be silently modified.

#### 4.6 Complete right-to-erasure workflow

- define full deletion lifecycle across DB, cache, logs, analytics, and backups.
- implement deletion request tracking and execution verification.
- define legal and operational retention exceptions explicitly.

#### 4.7 Security monitoring and hardening

- add authentication failure monitoring.
- add suspicious access monitoring for guardian endpoints.
- protect against abuse, prompt injection surfaces, and denial-of-wallet patterns.
- add secure headers, CSRF considerations where applicable, and CORS hardening.

#### 4.8 Conduct formal security review

- perform threat modeling.
- run dependency and container scanning.
- run secret scanning.
- run authenticated and unauthenticated penetration tests before launch.

### Exit Criteria

Privacy and security are production-ready when:

- sensitive workflows are enforced server-side
- consent and guardian access are verifiable end to end
- deletion, audit, and encryption policies are implemented and tested
- there are no known high-severity security gaps blocking launch

---

## 5. Infra and DevOps

### Objective

Build a deployable, observable, recoverable platform that can be operated safely in production.

### Required Work

#### 5.1 Define environments and release flow

- establish local, CI, staging, and production environments.
- define promotion rules between environments.
- add branch protections and required checks.
- adopt repeatable release workflows.

#### 5.2 Productionize container and deployment strategy

- review Dockerfiles for minimal runtime images.
- ensure health checks match real readiness.
- define resource requests and limits.
- make deployment manifests reflect the actual architecture.

#### 5.3 Complete CI/CD

- add automated lint, type, unit, integration, and build jobs.
- add migration checks.
- add container build and scan jobs.
- add release and rollback workflows.

#### 5.4 Observability completion

- define logs, metrics, and traces for all critical services.
- add dashboards tied to SLOs, not just generic technical metrics.
- instrument user-journey metrics such as lesson generation success rate, diagnostic completion, consent completion, and report generation latency.
- add alerting with on-call friendly thresholds.

#### 5.5 Reliability engineering basics

- define backup and restore for Postgres.
- define Redis durability expectations.
- rehearse restore drills.
- define incident severity levels and response playbooks.

#### 5.6 Queue and worker operations

- productionize Celery workers and scheduled jobs.
- monitor retries, dead-letter behavior, and queue age.
- isolate workloads by priority if needed.

#### 5.7 IaC and environment parity

- choose one primary infrastructure-as-code path and make it authoritative.
- remove ambiguity between Docker-only, Bicep, Kubernetes, and Supabase deployment stories.
- document which deployment models are supported now versus later.

#### 5.8 Cost and capacity planning

- estimate model-provider cost per learner journey.
- define caching and fallback strategy to control AI cost.
- plan scaling thresholds for API, DB, and workers.

### Exit Criteria

Infra and DevOps are production-ready when:

- deployments are automated and reversible
- observability supports detection and diagnosis
- backups and recovery are tested
- production capacity and cost envelopes are understood

---

## 6. Test Coverage and Quality Assurance

### Objective

Move from selective testing to comprehensive confidence across regulated and revenue-critical workflows.

### Required Work

#### 6.1 Expand backend test coverage

Add strong tests for:

- auth flows
- consent flows
- deletion flows
- orchestration paths
- policy enforcement
- cache behavior
- retry and failover logic
- migration safety
- structured error responses

#### 6.2 Expand frontend test coverage

Add:

- component tests
- interaction tests
- accessibility tests
- API mocking for failure modes
- route-level integration tests

#### 6.3 Add end-to-end tests

Cover at minimum:

- learner onboarding
- guardian consent
- lesson generation
- diagnostic session completion
- study plan generation
- parent report generation
- data deletion request

#### 6.4 Add contract tests

- validate frontend-backend API compatibility.
- validate provider response parsing assumptions.
- validate prompt-output schema compatibility.

#### 6.5 Add non-functional testing

- load testing for lesson generation endpoints.
- concurrency testing around async APIs.
- chaos testing around provider failure and Redis outages.
- restore testing for database backup and recovery.

#### 6.6 Test data strategy

- create factories and fixtures for core domain objects.
- separate deterministic test data from seeded demo data.
- create privacy-safe synthetic learner data.

#### 6.7 Quality gates in CI

- require passing tests before merge.
- set minimum coverage thresholds for critical modules.
- block release on failing migrations, lint, or security scans.

### Exit Criteria

Test and QA readiness is achieved when:

- all critical user journeys have automated coverage
- policy and privacy guarantees are regression tested
- load and failure conditions have been exercised before launch

---

## 7. Data and AI Governance

### Objective

Make the AI portion of the product reliable, explainable, observable, and safe for educational use.

### Required Work

#### 7.1 Prompt management discipline

- move prompts out of hardcoded strings into versioned templates.
- track prompt versions tied to outputs.
- allow controlled review by curriculum and product stakeholders.

#### 7.2 Output quality validation

- validate lesson, study plan, and report outputs against schemas.
- score outputs for educational completeness and policy safety.
- quarantine invalid outputs instead of surfacing raw failures.

#### 7.3 Provider fallback governance

- define explicit fallback order and conditions.
- ensure output quality and formatting expectations remain consistent across providers.
- monitor fallback rate and quality degradation.

#### 7.4 AI observability

Track:

- success rate by provider
- latency by provider
- schema failure rate
- content rejection rate
- fallback frequency
- cost per request
- prompt version effectiveness

#### 7.5 Human review loop

- create moderation or review workflows for problematic outputs.
- create educator feedback loops for lesson usefulness and correctness.
- define release gates for prompt changes.

#### 7.6 Educational correctness checks

- create subject and grade-level validations for CAPS alignment.
- test multilingual content quality.
- establish rules for age-appropriate wording and complexity.

### Exit Criteria

AI governance is production-ready when:

- outputs are validated and observable
- prompts are versioned and reviewable
- provider instability does not silently lower quality
- educational quality has measurable controls

---

## 8. Product and Accessibility Readiness

### Objective

Ensure the platform is genuinely usable for the target learner population in real-world South African conditions.

### Required Work

#### 8.1 Multilingual readiness

- implement true support for all intended languages incrementally and honestly.
- distinguish between UI translation, lesson-language generation, and linguistic QA.
- verify curriculum terminology quality per language.

#### 8.2 Low-connectivity readiness

- add offline-friendly caching for lessons and study plans.
- optimize payload sizes.
- support degraded network conditions.
- define synchronization rules after reconnect.

#### 8.3 Young learner accessibility

- add voice support where needed for Grade R to Grade 1 learners.
- simplify reading loads appropriately.
- test with child-friendly interaction patterns.

#### 8.4 Session continuity

- support resumable diagnostics.
- persist lesson progress where needed.
- recover from refreshes and network drops.

#### 8.5 Guardian experience maturity

- create clear consent flows.
- provide transparent data control actions.
- support downloadable records and deletion tracking.
- ensure guardian flows are not demo-only.

### Exit Criteria

Product readiness is achieved when:

- the platform works under realistic learner device and connectivity conditions
- multilingual and guardian claims match actual behavior
- key journeys are complete, usable, and trustworthy

---

## 9. Documentation and Team Enablement

### Objective

Make the system understandable and operable by a team, not just by the current author.

### Required Work

#### 9.1 Align documentation with reality

- update README, setup, deployment, and architecture docs.
- remove overstatements about production readiness until supported.
- document supported workflows and known limitations.

#### 9.2 Add contribution and engineering docs

- add `CONTRIBUTING.md`.
- define coding standards, branching rules, and review expectations.
- document local development and test workflows.

#### 9.3 Add runbooks

Create runbooks for:

- deployment
- rollback
- incident response
- database restore
- provider outage handling
- deletion request handling

#### 9.4 Add ownership maps

- define ownership for core modules.
- document dependency map for critical workflows.
- label high-risk components and operational dependencies.

### Exit Criteria

Documentation is production-ready when:

- a new engineer can set up, change, test, and deploy safely
- operators have practical runbooks
- docs reflect the true platform state

---

## 10. Recommended Execution Phases

## Phase 0: Truth and Stabilization

Focus:

- eliminate architecture drift
- update docs to match reality
- remove dead code
- remove direct browser-to-LLM calls
- fix auth and secret hygiene blockers

Exit:

- no critical security shortcuts remain
- the repo tells the truth about the platform

## Phase 1: Core Production Safety

Focus:

- strict API schemas
- orchestration and audit enforcement
- migration-only DB lifecycle
- proper auth and consent validation
- async correctness and provider timeout handling

Exit:

- regulated workflows are enforced and testable

## Phase 2: Operational Readiness

Focus:

- CI/CD completion
- observability and alerting
- durable persistence and caching strategy
- backup, restore, and incident playbooks
- worker and queue hardening

Exit:

- the system can be deployed, monitored, and recovered safely

## Phase 3: Product Hardening

Focus:

- frontend modularization
- accessibility and offline support
- guardian portal maturity
- stateful diagnostics and resumability
- multilingual expansion based on quality gates

Exit:

- the product is usable in realistic field conditions

## Phase 4: Scale and Optimization

Focus:

- performance tuning
- cost controls
- prompt governance
- AI quality analytics
- educator feedback loops and RLHF execution

Exit:

- the system scales with measurable quality and cost discipline

---

## 11. Launch Readiness Checklist

The project should not be called truly production-grade until all of the following are true:

- browser clients cannot directly call AI providers
- guardian authentication is real and enforced
- consent is auditable and not just presented in UI
- DB schema changes are migration-driven
- secrets are managed securely
- backup and restore have been tested
- critical workflows have end-to-end tests
- observability and alerts exist for the learner journey
- deletion workflows are implemented and verified
- docs accurately represent the current system

---

## 12. Final Recommendation

The project is close to a strong production-capable foundation, but it needs a consolidation and hardening program before launch claims should be made. The immediate priority is not adding more features. It is enforcing the correct architecture, removing unsafe shortcuts, strengthening auth and privacy guarantees, and building operational confidence.

If executed in the phase order above, EduBoost SA can evolve from a polished MVP into a credible, safe, and maintainable production platform.
