# EduBoost SA Implementation Improvement Roadmap
**Five-Pillar Constitutional Architecture · Phases 1–4**

This document consolidates the technical improvement backlog for EduBoost SA, combining the original Phase 1–3 roadmap with a detailed review of the current codebase. Items are grouped by severity and strategic impact. [cite_start]Each todo is actionable with a clear scope and rationale. [cite: 2, 3]

## Phases at a Glance
[cite_start]Phases are colour-coded based on priority and focus areas: [cite: 4, 6]

| Phase | Focus | Description |
| :--- | :--- | :--- |
| 🔴 **Phase 1** | Critical Bugs & Security | Fix Before Any User Traffic (6 items) |
| 🟠 **Phase 2** | Pipeline Completion | Wire Up Missing Five-Pillar Paths (5 items) |
| 🟡 **Phase 3** | Optimisation & Developer Experience | Reduce fragility and improve maintainability (5 items) |
| 🟢 **Phase 4** | Pedagogical & Accessibility Hardening | Deepen educational quality and broaden accessibility (5 items) |

---

## 🔴 Phase 1: Critical Bugs & Security
*Must be resolved before any real learner traffic. These items involve broken functionality, POPIA exposure, or authentication bypass.* [cite: 7]

1.  [cite_start]**Delete `app/api/services/lessons_router.py`** [cite: 8]
    * **Rationale:** This file is a dead draft superseded by `app/api/routers/lessons.py`. It contains non-existent imports (`from orchestrator import OperationRequest`) that cause `ImportError`.
    * **Action:** Remove the file entirely and add a linting rule to prevent future accumulation of dead code.

2.  [cite_start]**Fix guardian authentication: verify guardian exists before minting JWT** [cite: 9]
    * **Rationale:** The `POST /api/v1/auth/guardian/login` handler currently returns a signed JWT without verifying if the `learner_pseudonym_id` exists or if the email matches stored records.
    * **Action:** Add a database lookup against `learner_identities` to decrypt and compare stored emails before issuing tokens. Return HTTP 401 on failure.

3.  [cite_start]**Route frontend lesson generation through the FastAPI backend, not the Anthropic API directly** [cite: 10]
    * **Rationale:** `EduBoostApp.jsx` currently calls Anthropic directly, bypassing the Judiciary, Fourth Estate audit, and PII scrubber. This exposes PII and violates POPIA.
    * **Action:** Replace `callClaude()` in the frontend with a call to the backend `/api/v1/lessons/generate`. Remove all direct Anthropic calls from the frontend.

4.  [cite_start]**Upgrade learner ID hashing to use a salted SHA-256 (HMAC)** [cite: 11]
    * **Rationale:** Current plain SHA-256 hashes of UUIDs are vulnerable to brute-force reversal.
    * **Action:** Replace plain hashing in `orchestrator.py` and `profiler.py` with `hmac.new(SALT.encode(), learner_id.encode(), 'sha256')` using a secret `ENCRYPTION_SALT`.

5.  [cite_start]**Replace the synchronous `Anthropic()` client with `AsyncAnthropic()`** [cite: 12]
    * **Rationale:** The blocking synchronous client in `inference_gateway.py` stalls the FastAPI event loop for 2–8 seconds per call, serializing all requests under load.
    * **Action:** Implement `AsyncAnthropic()` and use `await client.messages.create(...)`.

6.  **Validate LLM JSON output with Pydantic before it reaches downstream layers** [cite: 13]
    * **Rationale:** Schema mismatches in LLM output currently cause opaque 500 errors.
    * **Action:** Wrap parsing with `model_validate()` and catch `ValidationError`. Return HTTP 422 with structured errors instead of raw LLM output.

---

## 🟠 Phase 2: Pipeline Completion
*The five-pillar architecture is designed but only partially wired. [cite_start]These items close the gaps between the design and what is actually executed at runtime.* [cite: 14]

7.  [cite_start]**Wire `FourthEstate` singleton to `settings.REDIS_URL`** [cite: 15]
    * **Rationale:** The audit bus currently defaults to an in-memory `deque` capped at 1000 events, which is lost on restart.
    * **Action:** Update the factory to use `FourthEstate(redis_url=settings.REDIS_URL, ...)` to activate the permanent regulatory-grade audit trail.

8.  [cite_start]**Implement Redis read/write in the Ether Profiler (Pillar 5)** [cite: 16]
    * **Rationale:** The profiler currently returns default profiles and never saves computed archetypes to Redis, causing every lesson to use default tone parameters.
    * **Action:** Implement Redis `get` and `setex` logic in `EtherProfiler` to store and retrieve `LearnerEtherProfile` data.

9.  [cite_start]**Add `GENERATE_STUDY_PLAN` and `GENERATE_PARENT_REPORT` to `ActionType` and route through Orchestrator** [cite: 17]
    * **Rationale:** These endpoints currently bypass the Orchestrator, Judiciary, and Fourth Estate audit bus.
    * **Action:** Update the `ActionType` enum, add constitutional rules (POPIA_01, PII_01) to the corpus, and route these actions through the Orchestrator.

10. [cite_start]**Implement lesson caching and return `lesson_id` from the generation endpoint** [cite: 18]
    * **Rationale:** Generated lessons are currently not stored, causing the `GET /api/v1/lessons/{lesson_id}` endpoint to always return 404.
    * **Action:** Generate a UUID `lesson_id` upon generation, store the JSON in Redis with `SETEX`, and include the ID in the API response.

11. [cite_start]**Add input schema validation to `generate_study_plan` and `generate_parent_report`** [cite: 19]
    * **Rationale:** Current functions accept raw primitives, potentially allowing PII to bypass Judiciary review.
    * **Action:** Create `StudyPlanParams` and `ParentReportParams` Pydantic models with strict validation to reject unknown keys.

---

## 🟡 Phase 3: Optimisation & Developer Experience
[cite_start]*These items reduce fragility, improve maintainability, and close subtle correctness issues.* [cite: 20]

12. [cite_start]**Add a Redis circuit breaker and local-log fallback to the Fourth Estate audit bus** [cite: 21]
    * **Rationale:** If Redis is down, audit events are currently lost.
    * **Action:** Implement a circuit breaker that falls back to a local JSONL log file after three failures and emits Prometheus metrics.

13. [cite_start]**Reconcile PII regex patterns between `inference_gateway.py` and `judiciary.py`** [cite: 22]
    * **Rationale:** Different files use different regex for South African phone numbers (some missing 08x and 09x ranges).
    * **Action:** Centralize patterns in `app/api/core/pii_patterns.py` and add regression tests for mastery scores (e.g., ensuring `0.62` isn't flagged as a number).

14. [cite_start]**Externalise prompt strings into Jinja2 templates in a `/prompts` directory** [cite: 23]
    * **Rationale:** Prompts are currently hardcoded in Python, making it difficult for curriculum experts to edit them without touching code.
    * **Action:** Move prompts to `.jinja2` files and wire them to the existing `PromptTemplate` database table for RLHF tracking.

15. [cite_start]**Document Ether archetypes and add a seeding fixture for development** [cite: 24]
    * **Rationale:** Kabbalistic names like `KETER` and `YESOD` are opaque to new contributors.
    * **Action:** Add a docstring mapping archetypes to behavioral meanings and create a test fixture factory for integration testing.

16. [cite_start]**Separate `--cov` flags into a dedicated `make coverage` target** [cite: 25]
    * **Rationale:** Running coverage on every test adds significant overhead to the TDD loop.
    * **Action:** Move coverage flags from `pytest.ini` to a `Makefile` or `pyproject.toml` to keep standard test runs fast.

---

## 🟢 Phase 4: Pedagogical & Accessibility Hardening
[cite_start]*Focuses on Grade R–1 voice interaction, stateful diagnostics, and offline support.* [cite: 26]

17. [cite_start]**Implement the STT/TTS gateway for Grade R–1 voice interaction** [cite: 27]
    * **Rationale:** Young learners (ages 5–7) cannot always read; voice interaction is required for accessibility.
    * **Action:** Create a `VoiceGateway` wrapping a provider like Whisper, handle transcript PII scrubbing, and add `GENERATE_VOICE_RESPONSE` logic.

18. [cite_start]**Convert the diagnostic endpoint into a stateful real-time session** [cite: 28]
    * **Rationale:** The current endpoint simulates answers rather than conducting a real session.
    * **Action:** Implement `/session/start` and `/session/{id}/answer` endpoints, storing Item Response Theory (IRT) state in Redis.

19. [cite_start]**Refactor the Judiciary to use a Strategy Pattern for subject-specific rule sets** [cite: 29]
    * **Rationale:** Validation rules for Maths vs. Language will diverge as the system grows.
    * **Action:** Implement a `JudiciaryStrategy` protocol to allow adding new subjects via specific strategy instances rather than complex `if/else` chains.

20. [cite_start]**Implement Celery tasks for the RLHF feedback loop and weekly study plan regeneration** [cite: 30]
    * **Rationale:** Infrastructure for Celery exists, but no tasks are running.
    * **Action:** Create tasks for nightly feedback processing (RLHF) and Sunday night study plan regeneration.

21. [cite_start]**Add offline-mode service worker and local lesson cache for low-connectivity learners** [cite: 31]
    * **Rationale:** Many South African learners have intermittent internet access.
    * **Action:** Implement a Next.js service worker using IndexedDB to cache the last 5 lessons and current study plan.

---

## Dependency Map
[cite_start]*Complete items in the indicated sequence within each phase.* [cite: 32, 33, 34]

| # | Item | Must complete first |
| :--- | :--- | :--- |
| 3 | Route frontend through backend | 5 (Async client) |
| 5 | Async Anthropic client | — |
| 6 | LLM output validation | — |
| 7 | Wire Fourth Estate to Redis | — |
| 8 | Ether Profiler Redis caching | 7 (Redis confirmed) |
| 9 | Orchestrator: new operations | 6 (Output val), 11 (Input schemas) |
| 10 | Lesson caching | 7 (Redis confirmed) |
| 11 | Input schemas for plan/report | — |
| 12 | Fourth Estate circuit breaker | 7 |
| 14 | Externalise prompts | 6 (Output validation stable) |
| 18 | Stateful diagnostic session | 7 (Redis for state) |
| 20 | Celery RLHF tasks | 6 (Reliable output), 10 (IDs in DB) |
| 21 | Offline mode | 18 (Stateful architecture) |

---
*Built with Ubuntu — “I am because we are.” [cite_start]Every South African child deserves quality, personalised education.* [cite: 35]