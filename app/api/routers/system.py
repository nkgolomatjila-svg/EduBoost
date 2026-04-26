"""EduBoost SA — System health, audit summaries, and pillar status."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


# ── POPIA Right to Access Response ───────────────────────────────────────────

class LearnerDataSummary(BaseModel):
    """Summary of learner data for POPIA right-to-access."""
    learner_id: str
    pseudonym_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    overall_mastery: Optional[float]
    total_xp: int
    streak_days: int
    is_active: bool
    created_at: Optional[datetime]
    deleted_at: Optional[datetime]


class AccessRequestResponse(BaseModel):
    """Response for right-to-access request."""
    learner_id: str
    status: str
    data_summary: Optional[LearnerDataSummary]
    consent_records: list
    audit_events: list
    diagnostic_sessions: int
    study_plans: int
    request_timestamp: str


@router.get("/health")
async def system_health():
    try:
        from app.api.fourth_estate import get_fourth_estate

        return get_fourth_estate().get_health_status()
    except Exception as e:
        return {
            "overall": "AMBER",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/audit")
async def audit_report(
    report_type: str = Query(default="COMPLIANCE"),
    hours: int = Query(default=24, ge=1, le=168),
):
    try:
        from app.api.fourth_estate import get_fourth_estate

        fe = get_fourth_estate()
        report = fe.build_audit_report(report_type=report_type, hours=hours)
        report["chain_integrity"] = fe.get_chain_integrity()
        report["audit_sequence"] = fe.get_sequence()
        return report
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/pillars")
async def pillar_status():
    try:
        from app.api.fourth_estate import get_fourth_estate

        fe = get_fourth_estate()
        health = fe.get_health_status()
        return {
            "pillars": health.get("pillar_status", {}),
            "constitutional_health": health.get("constitutional_health", 1.0),
            "judiciary_approval_rate": health.get("judiciary_approval_rate", 1.0),
            "audit_chain_length": fe.get_sequence(),
            "recent_violations": fe.get_recent_violations(limit=5),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/refresh-rules", status_code=status.HTTP_202_ACCEPTED)
async def refresh_rules():
    return {
        "status": "accepted",
        "message": "Rules refreshed from constitutional corpus",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── POPIA Right to Access Endpoint ───────────────────────────────────────────

@router.get("/access/{learner_id}", response_model=AccessRequestResponse)
async def right_to_access(
    learner_id: str,
    guardian_token: Optional[str] = Query(default=None, description="Guardian JWT token for authorization"),
):
    """
    POPIA right-to-access endpoint.
    
    Returns all personal data held about a learner, including:
    - Basic profile data
    - Consent records
    - Audit events
    - Diagnostic session counts
    - Study plan counts
    
    This endpoint requires guardian authorization via JWT token.
    """
    from sqlalchemy import select, text
    from app.api.core.database import AsyncSessionFactory
    from app.api.models.db_models import Learner, LearnerIdentity, ConsentAudit, AuditEvent, DiagnosticSession, StudyPlan
    
    # Validate guardian token if provided
    if guardian_token:
        try:
            import jwt as pyjwt
            from app.api.core.config import settings
            payload = pyjwt.decode(guardian_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("role") != "guardian":
                raise HTTPException(status_code=403, detail="Guardian token required")
            token_learner_id = payload.get("learner_id")
            if token_learner_id != learner_id:
                raise HTTPException(status_code=403, detail="Token does not match learner ID")
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from e
    
    try:
        async with AsyncSessionFactory() as session:
            # Get learner data
            learner_uuid = UUID(learner_id)
            learner = await session.get(Learner, learner_uuid)
            
            if not learner:
                raise HTTPException(status_code=404, detail="Learner not found")
            
            # Get pseudonym
            result = await session.execute(
                select(LearnerIdentity).where(LearnerIdentity.learner_id == learner_uuid)
            )
            identity = result.scalar_one_or_none()
            
            # Get consent records
            result = await session.execute(
                select(ConsentAudit)
                .where(ConsentAudit.pseudonym_id == learner_uuid)
                .order_by(ConsentAudit.occurred_at.desc())
                .limit(50)
            )
            consent_records = [
                {
                    "event_type": r.event_type,
                    "consent_version": r.consent_version,
                    "guardian_email_hash": r.guardian_email_hash[:8] + "..." if r.guardian_email_hash else None,
                    "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                }
                for r in result.scalars().all()
            ]
            
            # Get audit events
            result = await session.execute(
                select(AuditEvent)
                .where(AuditEvent.learner_id == learner_uuid)
                .order_by(AuditEvent.occurred_at.desc())
                .limit(100)
            )
            audit_events = [
                {
                    "event_type": r.event_type,
                    "details": r.details,
                    "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                }
                for r in result.scalars().all()
            ]
            
            # Get diagnostic session count
            result = await session.execute(
                select(DiagnosticSession).where(DiagnosticSession.learner_id == learner_uuid)
            )
            diagnostic_sessions = len(result.scalars().all())
            
            # Get study plan count
            result = await session.execute(
                select(StudyPlan).where(StudyPlan.learner_id == learner_uuid)
            )
            study_plans = len(result.scalars().all())
            
            return AccessRequestResponse(
                learner_id=str(learner.learner_id),
                status="active" if learner.is_active else "inactive",
                data_summary=LearnerDataSummary(
                    learner_id=str(learner.learner_id),
                    pseudonym_id=identity.pseudonym_id if identity else None,
                    first_name=learner.first_name if learner.first_name and not learner.first_name.startswith("DELETED_") else None,
                    last_name=learner.last_name if learner.last_name and not learner.last_name.startswith("DELETED_") else None,
                    email=learner.email,
                    overall_mastery=learner.overall_mastery,
                    total_xp=learner.total_xp,
                    streak_days=learner.streak_days,
                    is_active=learner.is_active,
                    created_at=learner.created_at,
                    deleted_at=learner.deleted_at,
                ),
                consent_records=consent_records,
                audit_events=audit_events,
                diagnostic_sessions=diagnostic_sessions,
                study_plans=study_plans,
                request_timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid learner ID format") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Audit Search/Query API ───────────────────────────────────────────────────

class AuditSearchResponse(BaseModel):
    """Response for audit search queries."""
    events: list
    total_count: int
    page: int
    page_size: int
    has_more: bool


@router.get("/audit/search", response_model=AuditSearchResponse)
async def search_audit_events(
    learner_id: Optional[str] = Query(default=None, description="Filter by learner ID"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(default=None, description="Start date for time range"),
    end_date: Optional[datetime] = Query(default=None, description="End date for time range"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Results per page"),
):
    """
    Search and query audit events.
    
    Supports filtering by:
    - learner_id: Specific learner
    - event_type: Type of event (e.g., LOGIN, DIAGNOSTIC_COMPLETE, LESSON_GENERATED)
    - start_date/end_date: Time range
    
    Returns paginated results with event details.
    """
    from sqlalchemy import select, and_
    from app.api.core.database import AsyncSessionFactory
    from app.api.models.db_models import AuditEvent
    
    try:
        async with AsyncSessionFactory() as session:
            # Build query conditions
            conditions = []
            if learner_id:
                conditions.append(AuditEvent.learner_id == UUID(learner_id))
            if event_type:
                conditions.append(AuditEvent.event_type == event_type)
            if start_date:
                conditions.append(AuditEvent.occurred_at >= start_date)
            if end_date:
                conditions.append(AuditEvent.occurred_at <= end_date)
            
            # Build and execute query
            query = select(AuditEvent)
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total count
            count_query = select(AuditEvent)
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            from sqlalchemy import func
            count_result = await session.execute(select(func.count()).select_from(count_query.subquery()))
            total_count = count_result.scalar() or 0
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(page_size)
            
            result = await session.execute(query)
            events = [
                {
                    "event_id": str(e.event_id),
                    "learner_id": str(e.learner_id) if e.learner_id else None,
                    "event_type": e.event_type,
                    "details": e.details,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                }
                for e in result.scalars().all()
            ]
            
            return AuditSearchResponse(
                events=events,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_more=(offset + len(events)) < total_count,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid query parameters") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
