# EduBoost SA Production Roadmap Issue Tracker

This document tracks the full set of 236 actionable items required to move EduBoost SA to true production grade. Each item is intentionally written as a trackable work unit.

## Status Key

- [ ] Not started
- [~] In progress
- [x] Complete
- [!] Blocked

---

## 1. Architecture

1. [ ] Define the single authoritative target architecture for production.
2. [ ] Document the approved runtime components: frontend, API, Postgres, Redis, Celery workers, monitoring, and external AI providers.
3. [ ] Decide which infrastructure path is primary: Docker, Kubernetes, Bicep, or Supabase-backed hybrid.
4. [ ] Remove or rewrite README sections that describe non-existent folders or unsupported deployment flows.
5. [ ] Delete dead or duplicate backend modules that no longer belong to the active architecture.
6. [ ] Standardize one approved path for lesson generation.
7. [ ] Standardize one approved path for study plan generation.
8. [ ] Standardize one approved path for parent report generation.
9. [ ] Ensure every regulated workflow passes through orchestration, validation, audit, and privacy controls.
10. [ ] Separate code into clear layers: routers, schemas, services, adapters, persistence, policy/compliance.
11. [ ] Define which workflows are synchronous and which must run asynchronously.
12. [ ] Identify all domain events that require audit logging.
13. [ ] Define service-level objectives for latency, uptime, and recovery.
14. [ ] Create an architecture decision record for major technical choices.
15. [ ] Add a dependency map showing which modules are production-critical.

## 2. Backend Quality

16. [ ] Remove insecure secret defaults from configuration.
17. [ ] Make production startup fail when required secrets are missing.
18. [ ] Create separate config profiles for local, test, staging, and production.
19. [ ] Audit every route for missing request and response schemas.
20. [ ] Add strict Pydantic models to every route.
21. [ ] Reject unknown input fields for sensitive endpoints.
22. [ ] Standardize API error responses.
23. [ ] Add API versioning rules and document them.
24. [ ] Remove runtime table creation from application startup.
25. [ ] Use Alembic as the only database schema migration path.
26. [ ] Add migration verification to CI.
27. [ ] Create rollback instructions for failed migrations.
28. [ ] Replace blocking SDK usage in async request paths.
29. [ ] Review all external I/O for correct timeout behavior.
30. [ ] Add retry policies with bounded backoff for external AI calls.
31. [ ] Add circuit breakers around provider failures.
32. [ ] Add idempotency protection for retry-prone write operations.
33. [ ] Persist generated lessons with durable IDs.
34. [ ] Persist generated study plans where product history is required.
35. [ ] Persist parent reports where product history is required.
36. [ ] Define cache versus database ownership for every generated artifact.
37. [ ] Validate LLM JSON against Pydantic models before downstream use.
38. [ ] Add business-rule validation for grade, subject, language, and mastery values.
39. [ ] Deduplicate and reorganize dependencies in `requirements.txt`.
40. [ ] Split runtime dependencies from dev/test dependencies.
41. [ ] Add structured logging conventions across backend modules.
42. [ ] Add correlation/request IDs to logs.
43. [ ] Introduce rate limiting on high-cost and abuse-prone endpoints.
44. [ ] Add graceful degradation behavior for provider outages.
45. [ ] Review all routers for consistency in naming, status codes, and error handling.
46. [ ] Remove stale experimental logic from the request path.
47. [ ] Add repository-level coding standards for backend modules.

## 3. Frontend Quality

48. [ ] Break `EduBoostApp.jsx` into smaller feature modules.
49. [ ] Create separate components for onboarding, dashboard, diagnostics, lessons, study plan, badges, and parent portal.
50. [ ] Move inline style definitions into a maintainable styling system.
51. [ ] Create a centralized frontend API client.
52. [ ] Remove all direct LLM provider calls from the browser.
53. [ ] Route all AI interactions through backend endpoints only.
54. [ ] Separate mock/demo data from production logic.
55. [ ] Define a frontend state management strategy.
56. [ ] Separate server state from local UI state.
57. [ ] Standardize loading states across all screens.
58. [ ] Standardize error states across all screens.
59. [ ] Standardize retry behavior for failed API calls.
60. [ ] Add proper empty states where data may not yet exist.
61. [ ] Make learner sessions resumable after refresh where appropriate.
62. [ ] Make diagnostic sessions resumable.
63. [ ] Persist lesson progress if product requirements demand it.
64. [ ] Add responsive behavior for smaller mobile devices.
65. [ ] Add keyboard navigation across all core flows.
66. [ ] Improve screen-reader semantics.
67. [ ] Ensure color contrast meets accessibility standards.
68. [ ] Add focus states for interactive elements.
69. [ ] Reduce oversized component responsibilities.
70. [ ] Introduce reusable UI primitives for buttons, cards, badges, banners, and forms.
71. [ ] Review local storage/session storage usage for sensitive data exposure.
72. [ ] Ensure guardian-specific flows are clearly separated from learner flows.
73. [ ] Add frontend error telemetry for critical failures.
74. [ ] Add route-level tests for major app flows.

## 4. Privacy and Security

75. [ ] Move all privacy-sensitive enforcement from UI messaging into backend logic.
76. [ ] Verify guardian identity before issuing guardian JWTs.
77. [ ] Verify guardian-to-learner relationship before granting access.
78. [ ] Add role-based authorization rules.
79. [ ] Add context-aware authorization for sensitive endpoints.
80. [ ] Define token expiry, rotation, and revocation behavior.
81. [ ] Centralize PII detection patterns in one module.
82. [ ] Reconcile inconsistencies in current scrubber rules.
83. [ ] Add tests to ensure learner IDs never reach AI providers.
84. [ ] Add tests to ensure guardian email never reaches AI providers.
85. [ ] Review all logs for accidental PII leakage.
86. [ ] Replace weak identifier hashing patterns with keyed hashing where required.
87. [ ] Define encryption key rotation procedures.
88. [ ] Move secrets into a managed secret store for production.
89. [ ] Add secret scanning to CI.
90. [ ] Harden CORS policy for production.
91. [ ] Add secure response headers where applicable.
92. [ ] Review CSRF exposure for auth/session flows.
93. [ ] Add monitoring for authentication failures and suspicious access.
94. [ ] Define and implement right-to-erasure across database, cache, logs, and analytics.
95. [ ] Track deletion requests through a verifiable lifecycle.
96. [ ] Define backup retention interactions with deletion policy.
97. [ ] Add threat modeling for learner, guardian, AI-provider, and admin attack surfaces.
98. [ ] Run dependency vulnerability scanning.
99. [ ] Run container image scanning.
100. [ ] Plan and perform penetration testing before launch.

## 5. Infra and DevOps

101. [ ] Define local, CI, staging, and production environments.
102. [ ] Define branch protections and merge requirements.
103. [ ] Define the release promotion flow from staging to production.
104. [ ] Standardize Dockerfiles for lean runtime images.
105. [ ] Review health checks for actual readiness, not just liveness.
106. [ ] Add resource requests and limits for production deployments.
107. [ ] Decide whether Kubernetes manifests are actively supported.
108. [ ] Align deployment manifests with actual production architecture.
109. [ ] Add CI jobs for linting.
110. [ ] Add CI jobs for type checks where applicable.
111. [ ] Add CI jobs for backend unit tests.
112. [ ] Add CI jobs for frontend tests.
113. [ ] Add CI jobs for integration tests.
114. [ ] Add CI jobs for build verification.
115. [ ] Add CI jobs for migration checks.
116. [ ] Add CI jobs for security scans.
117. [ ] Add CI jobs for container builds.
118. [ ] Add release automation.
119. [ ] Add rollback automation or a documented rollback playbook.
120. [ ] Define logs, metrics, and traces that matter for operations.
121. [ ] Add learner-journey metrics such as lesson generation success rate.
122. [ ] Add diagnostic completion metrics.
123. [ ] Add consent completion metrics.
124. [ ] Add parent report generation latency metrics.
125. [ ] Add alerting thresholds tied to SLOs.
126. [ ] Implement backup automation for Postgres.
127. [ ] Define Redis durability expectations.
128. [ ] Test restore procedures regularly.
129. [ ] Add queue monitoring for Celery.
130. [ ] Add dead-letter or failure visibility for async tasks.
131. [ ] Add incident severity definitions.
132. [ ] Create incident response runbooks.
133. [ ] Estimate model-provider cost per core workflow.
134. [ ] Add cost controls through caching, quotas, or fallback policies.
135. [ ] Define scaling thresholds for API, DB, and worker services.

## 6. Test Coverage and Quality Assurance

136. [ ] Expand unit tests for auth flows.
137. [ ] Expand unit tests for consent flows.
138. [ ] Expand unit tests for deletion flows.
139. [ ] Expand unit tests for orchestration logic.
140. [ ] Expand unit tests for PII scrubber logic.
141. [ ] Expand unit tests for provider fallback logic.
142. [ ] Expand unit tests for schema validation failures.
143. [ ] Expand integration tests for lesson generation.
144. [ ] Add integration tests for guardian login and authorization.
145. [ ] Add integration tests for consent capture and audit logging.
146. [ ] Add integration tests for deletion requests.
147. [ ] Add integration tests for study plan generation.
148. [ ] Add integration tests for parent report generation.
149. [ ] Add contract tests between frontend and backend APIs.
150. [ ] Add contract tests for AI provider response parsing.
151. [ ] Add end-to-end tests for learner onboarding.
152. [ ] Add end-to-end tests for guardian consent.
153. [ ] Add end-to-end tests for diagnostic sessions.
154. [ ] Add end-to-end tests for lesson completion.
155. [ ] Add end-to-end tests for study plan viewing.
156. [ ] Add end-to-end tests for parent portal access.
157. [ ] Add end-to-end tests for data deletion requests.
158. [ ] Add accessibility testing in CI.
159. [ ] Add load tests for high-cost endpoints.
160. [ ] Add concurrency tests for async API safety.
161. [ ] Add chaos testing for provider outages.
162. [ ] Add chaos testing for Redis failures.
163. [ ] Add migration safety tests.
164. [ ] Create deterministic synthetic learner datasets for testing.
165. [ ] Define coverage thresholds for critical modules.
166. [ ] Make passing quality gates mandatory before merge.

## 7. Data and AI Governance

167. [ ] Move hardcoded prompts into versioned template files.
168. [ ] Track prompt versions in storage or metadata.
169. [ ] Define a review process for prompt changes.
170. [ ] Validate every AI output against strict schemas.
171. [ ] Reject or quarantine invalid AI output.
172. [ ] Track provider used, prompt version, and output validation status for each generation.
173. [ ] Define provider fallback order and rules.
174. [ ] Measure fallback frequency.
175. [ ] Measure output schema failure rates.
176. [ ] Measure AI response latency per provider.
177. [ ] Measure AI cost per generation path.
178. [ ] Add educator review workflows for sample generated lessons.
179. [ ] Add quality scoring for CAPS alignment.
180. [ ] Add quality scoring for age-appropriate language.
181. [ ] Add quality scoring for multilingual output quality.
182. [ ] Define release criteria for prompt changes.
183. [ ] Add AI content incident handling for low-quality or unsafe outputs.
184. [ ] Create a process for evaluating RLHF data quality before using it.
185. [ ] Ensure all AI telemetry remains privacy-safe.

## 8. Product and Accessibility Readiness

186. [ ] Audit the true state of multilingual support.
187. [ ] Separate UI translation support from lesson-language support.
188. [ ] Create a rollout plan for additional official languages.
189. [ ] Validate curriculum terminology quality per language.
190. [ ] Add offline-friendly caching for recent lessons.
191. [ ] Add offline-friendly caching for current study plans.
192. [ ] Define sync behavior after reconnect.
193. [ ] Optimize large payload sizes for low-bandwidth users.
194. [ ] Add voice support planning for early-grade learners if this remains a product goal.
195. [ ] Validate age-appropriate reading complexity by grade band.
196. [ ] Test product flows on lower-end Android devices.
197. [ ] Make diagnostic sessions stateful instead of simulated where needed.
198. [ ] Ensure guardian controls are functional, not just presentational.
199. [ ] Add downloadable learner data exports if product requirements require it.
200. [ ] Add request status visibility for deletion and privacy actions.
201. [ ] Validate usability with real target-user scenarios.
202. [ ] Add product analytics that do not compromise learner privacy.

## 9. Documentation and Team Enablement

203. [ ] Update `README.md` to reflect the actual repo state.
204. [ ] Add `CONTRIBUTING.md`.
205. [ ] Add engineering setup documentation for backend and frontend.
206. [ ] Add architecture documentation with diagrams.
207. [ ] Add deployment documentation for the supported environment.
208. [ ] Add rollback documentation.
209. [ ] Add incident response runbooks.
210. [ ] Add database backup and restore runbooks.
211. [ ] Add provider-outage handling runbooks.
212. [ ] Add deletion-request operational procedures.
213. [ ] Add coding standards documentation.
214. [ ] Add ownership mapping for major modules.
215. [ ] Add dependency maps for critical workflows.
216. [ ] Document known limitations and unsupported flows honestly.
217. [ ] Define release checklist documentation.
218. [ ] Define launch readiness checklist documentation.

## 10. Recommended Implementation Order

219. [ ] First, eliminate architecture drift and remove unsafe shortcuts.
220. [ ] Second, enforce backend correctness: auth, schemas, migrations, async safety, provider controls.
221. [ ] Third, modularize the frontend and remove demo-style patterns.
222. [ ] Fourth, complete privacy, deletion, and audit guarantees.
223. [ ] Fifth, productionize CI/CD, monitoring, backup, and restore.
224. [ ] Sixth, deepen automated coverage for all critical user journeys.
225. [ ] Seventh, harden AI governance, output quality, and educational correctness.
226. [ ] Eighth, expand multilingual, offline, and accessibility capabilities in a controlled way.

## 11. Immediate High-Priority Tasks

227. [ ] Remove all browser-direct AI provider calls.
228. [ ] Fix guardian authentication and authorization.
229. [ ] Remove runtime DB auto-create from production path.
230. [ ] Add strict schemas and validation to all critical endpoints.
231. [ ] Route all sensitive workflows through orchestration and auditing.
232. [ ] Persist generated lessons with durable IDs.
233. [ ] Add proper migration discipline.
234. [ ] Update the README to stop overstating current production readiness.
235. [ ] Break up `EduBoostApp.jsx`.
236. [ ] Add CI quality gates for tests, builds, and security scans.
