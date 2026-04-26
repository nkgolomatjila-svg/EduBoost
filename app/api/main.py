"""
EduBoost SA — FastAPI Application Entrypoint
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.api.core.config import settings
from app.api.routers import health, learners, lessons, diagnostic, study_plans, parent, auth, system, gamification, audit

log = structlog.get_logger()


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

class RateLimitMiddleware:
    """Simple in-memory rate limiter middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list[float]] = {}
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get client IP
        client_ip = scope.get("client", ("unknown", 0))[0]
        
        import time
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests and count recent ones
        if client_ip in self._requests:
            self._requests[client_ip] = [t for t in self._requests[client_ip] if t > minute_ago]
        else:
            self._requests[client_ip] = []
        
        # Check rate limit
        if len(self._requests[client_ip]) >= self.requests_per_minute:
            # Rate limited - return 429
            response = b'HTTP/1.1 429 Too Many Requests\r\nContent-Type: application/json\r\n\r\n{"detail":{"error":"Rate limit exceeded","code":"RATE_LIMIT_EXCEEDED"}}'
            await send({"type": "http.response.start", "status": 429, "headers": [[b"content-type", b"application/json"]]})
            await send({"type": "http.response.body", "body": response})
            return
        
        # Record this request
        self._requests[client_ip].append(now)
        
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("EduBoost SA API starting", env=settings.APP_ENV)
    log.info("DB schema management is migration-driven; runtime auto-create is disabled")
    yield
    log.info("EduBoost SA API shutting down")


# ── Sentry (production only) ─────────────────────────────────────────────────
if settings.SENTRY_DSN and settings.APP_ENV == "production":
    import sentry_sdk
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)

app = FastAPI(
    title="EduBoost SA API",
    description="AI-powered adaptive learning for South African learners — Grade R to Grade 7",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting middleware (60 req/min for general, stricter for auth)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# SlowAPI rate limiter for distributed deployments
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Add rate limit exception handler
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": {"error": "Rate limit exceeded", code: "RATE_LIMIT_EXCEEDED"}}
    )

# ── Prometheus metrics ────────────────────────────────────────────────────────
if settings.PROMETHEUS_ENABLED:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app)
    except ImportError:
        log.warning("prometheus_fastapi_instrumentator not installed, skipping metrics")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(learners.router, prefix="/api/v1/learners", tags=["Learners"])
app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["Lessons"])
app.include_router(diagnostic.router, prefix="/api/v1/diagnostic", tags=["Diagnostic"])
app.include_router(study_plans.router, prefix="/api/v1/study-plans", tags=["Study Plans"])
app.include_router(parent.router, prefix="/api/v1/parent", tags=["Parent Portal"])
app.include_router(gamification.router, prefix="/api/v1/gamification", tags=["Gamification"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])
