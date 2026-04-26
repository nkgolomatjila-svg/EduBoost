# 🦁 EduBoost SA

**AI-powered adaptive learning platform for South African learners — Grade R to Grade 7**

[![CAPS Aligned](https://img.shields.io/badge/CAPS-Aligned-green)](https://www.education.gov.za)
[![POPIA Compliant](https://img.shields.io/badge/POPIA-Compliant-blue)](https://popia.co.za)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)

---

## 📋 Overview

EduBoost SA is an adaptive learning platform under active production-hardening. The current repository contains a FastAPI backend, a Next.js frontend, local Docker-based infrastructure, and early observability/test foundations. It is not yet production-grade end to end.

### Key Features
- 🧠 **Adaptive Diagnostic Engine** — IRT-based (Item Response Theory) assessments that find the exact grade level of each knowledge gap
- 🤖 **AI Lesson Generation** — Claude/Llama 3 powered lessons with authentic South African context (ubuntu, braai, rands, local fauna)
- 📅 **Dynamic Study Plans** — CAPS-aligned weekly schedules that prioritise foundation gaps while keeping pace with grade-level work
- 🏆 **Gamification** — XP, badges, streaks for Grade R–3; discovery-based engagement for Grade 4–7
- 🔒 **Privacy-oriented design goals** — parental consent, pseudonymous learner IDs, data minimisation, and right-to-erasure targets are part of the roadmap
- 📊 **Parent Portal direction** — AI-generated progress reports and guardian visibility are present in concept and partial implementation

---

## 🗂️ Project Structure

```
eduboost-sa/
├── app/
│   ├── api/                          # FastAPI backend
│   │   ├── constitutional_schema/    # Schema and typing helpers
│   │   ├── core/                     # Config, DB, Celery
│   │   ├── ml/                       # IRT engine
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── routers/                  # API routes
│   │   ├── services/                 # LLM / lesson services
│   │   ├── main.py                   # FastAPI entrypoint
│   │   ├── orchestrator.py           # Workflow orchestration
│   │   ├── judiciary.py              # Policy / validation layer
│   │   ├── fourth_estate.py          # Audit/event support
│   │   └── profiler.py               # Profiling helpers
│   └── frontend/                     # Next.js frontend
│       ├── src/app/                  # App router entrypoints
│       ├── src/components/           # UI components (currently still monolithic)
│       └── package.json
├── docker/                           # Dockerfiles
├── grafana/                          # Grafana provisioning
├── k8s/                              # Kubernetes manifests
├── bicep/                            # Bicep IaC experiments
├── scripts/                          # DB init / seed scripts
├── tests/                            # Unit and integration tests
├── docker-compose.yml                # Local development stack
├── prometheus.yml                    # Prometheus scrape config
├── requirements.txt                  # Python dependencies
├── pytest.ini                        # Test configuration
├── Production_Grade_Roadmap.md       # Production hardening roadmap
└── README.md
```

---

## ⚠️ Current State

The current codebase already includes:

- backend-mediated lesson generation paths
- Docker-based local development with Postgres, Redis, Prometheus, Grafana, and Celery
- initial constitutional/orchestration concepts
- unit and integration tests for selected modules

Known gaps still being addressed:

- frontend architecture is still centered around a large `EduBoostApp.jsx` component, with some demo-era UI paths still being retired
- database lifecycle is not yet migration-driven in this repository
- authentication, consent, deletion, and audit guarantees are incomplete
- CI/CD and release automation are not yet defined in-repo
- earlier documentation overstated current production readiness

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
- A Postgres database for local development
- Redis for cache / worker development
- API keys for the providers you want to test

### 1. Clone & configure
```bash
git clone <your-gitlab-repo-url>
cd eduboost-sa
# Create a .env file manually for local development and provide the required values

cp env.example .env
```

### 2. Start the full stack (Docker)
```bash
cd app/frontend
npm install
npm fund

cd ../../
docker compose up --build
```

Services will be available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Flower | http://localhost:5555 |

### 3. Run without Docker (development)

**Backend:**
```bash
cd app/api
python -m venv ../../.venv
source ../../.venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r ../../requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd app/frontend
npm install
npm run dev
```

---

## 🔑 Environment Variables

Create a local `.env` file for development. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Async SQLAlchemy connection string |
| `REDIS_URL` | Redis connection string |
| `GROQ_API_KEY` | Primary LLM inference |
| `ANTHROPIC_API_KEY` | Secondary / fallback lesson provider |
| `SUPABASE_URL` | Optional Supabase URL if used |
| `SUPABASE_SERVICE_KEY` | Optional backend service key |
| `SUPABASE_ANON_KEY` | Optional frontend anon key |
| `JWT_SECRET` | JWT signing secret |
| `ENCRYPTION_KEY` | Encryption key for sensitive data |
| `ENCRYPTION_SALT` | Salt used with encryption / derivation flows |
| `SENTRY_DSN` | Optional Sentry DSN |

---

## 🧪 Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage report
pytest --cov=app --cov-report=html
```

---

## 🗃️ Database Migrations

Schema changes are moving to an Alembic-driven workflow.

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Runtime schema auto-creation is disabled. New schema changes should be added through `alembic/versions/`.

## 📦 Deployment

Deployment paths are still being consolidated. Today, the repository most clearly supports local Docker-based development via `docker-compose.yml`.

The presence of `k8s/` and `bicep/` reflects work-in-progress infrastructure options, not a finalized production deployment standard.

---

## 🔐 POPIA Alignment

EduBoost SA is being built with POPIA-aligned design goals, including:

1. **Data minimisation goals** — limit collection to the minimum needed for learning workflows.
2. **Pseudonymisation goals** — avoid passing direct learner identity into AI workflows.
3. **Parental consent** — intended as a required backend-enforced control before learner data use.
4. **Right to Erasure** — targeted as a tracked workflow, but not yet verified end to end across all stores.
5. **LLM Firewall** — lesson generation is routed through the backend; broader provider governance is still being hardened.
6. **Audit Trail** — audit-oriented components exist, but consent and access auditing are not yet complete across all workflows.

---

## 📈 Monitoring

The local stack includes Prometheus and Grafana. Dashboards and metrics exist as an early foundation, but observability is still being expanded toward learner-journey and operational SLO coverage.

---

## 🤝 Contributing

Contributing guidance and engineering workflows still need to be formalized. Until then:

1. Create a feature branch
2. Keep changes scoped
3. Add or update tests with behavior changes
4. Prefer roadmap-aligned hardening over new surface area

---

## 📜 License

MIT License — see `LICENSE` file.

---

## 🇿🇦 About

Built with Ubuntu — *"I am because we are."* Every South African child deserves access to quality, personalised education.
