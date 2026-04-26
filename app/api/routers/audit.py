"""EduBoost SA — Audit Query Router

Provides endpoints for querying and searching audit events
for compliance and transparency purposes.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.services.audit_query_service import AuditQueryService
from app.api.core.database import AsyncSessionFactory

router = APIRouter()


class AuditQueryRequest(BaseModel):
    """Request model for audit queries."""
    learner_id: Optional[UUID] = None
    event_type: Optional[str] = None
    pillar: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class AuditSearchRequest(BaseModel):
    """Request model for audit search."""
    query: str
    learner_id: Optional[UUID] = None
    limit: int = 50


@router.post("/query")
async def query_audit_events(request: AuditQueryRequest):
    """
    Query audit events with optional filtering.
    
    Query parameters:
    - learner_id: Filter by learner UUID
    - event_type: Filter by event type (e.g., ACTION_SUBMITTED, STAMP_ISSUED)
    - pillar: Filter by constitutional pillar (LEGISLATURE, EXECUTIVE, JUDICIARY, FOURTH_ESTATE)
    - start_date: Filter by start date (ISO 8601 format)
    - end_date: Filter by end date (ISO 8601 format)
    - limit: Maximum number of results (default: 100)
    - offset: Pagination offset (default: 0)
    """
    async with AsyncSessionFactory() as session:
        try:
            service = AuditQueryService(session)
            result = await service.query_events(
                learner_id=request.learner_id,
                event_type=request.event_type,
                pillar=request.pillar,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=request.limit,
                offset=request.offset,
            )
            return {"success": True, "data": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query failed: {e}") from e


@router.post("/search")
async def search_audit_events(request: AuditSearchRequest):
    """
    Search audit events by free-text query.
    
    Searches in event_type, pillar, and payload fields.
    """
    async with AsyncSessionFactory() as session:
        try:
            service = AuditQueryService(session)
            result = await service.search_events(
                query=request.query,
                learner_id=request.learner_id,
                limit=request.limit,
            )
            return {"success": True, "data": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e


@router.get("/learner/{learner_id}/trail")
async def get_learner_audit_trail(
    learner_id: UUID,
    days: int = Query(30, ge=1, le=365),
):
    """
    Get complete audit trail for a learner.
    
    Returns all audit events for a learner organized by category
    (access, modifications, consent, deletions, violations).
    """
    async with AsyncSessionFactory() as session:
        try:
            service = AuditQueryService(session)
            result = await service.get_learner_audit_trail(
                learner_id=learner_id,
                days=days,
            )
            return {"success": True, "data": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Audit trail retrieval failed: {e}") from e


@router.get("/compliance/report")
async def get_compliance_report(
    days: int = Query(90, ge=1, le=365),
):
    """
    Get a compliance report from audit events.
    
    Provides statistics on constitutional adherence, violations,
    rejections, and LLM performance.
    """
    async with AsyncSessionFactory() as session:
        try:
            service = AuditQueryService(session)
            result = await service.get_compliance_report(days=days)
            return {"success": True, "data": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compliance report generation failed: {e}") from e


@router.get("/recent")
async def get_recent_audit_events(limit: int = Query(50, ge=1, le=500)):
    """Get the most recent audit events."""
    from app.api.fourth_estate import get_fourth_estate

    try:
        fourth_estate = get_fourth_estate()
        recent = fourth_estate.get_recent_events(limit)
        
        return {
            "success": True,
            "count": len(recent),
            "events": [
                {
                    "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                    "pillar": event.pillar,
                    "learner_hash": event.learner_hash,
                    "action_id": event.action_id,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in recent
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent events: {e}") from e


@router.get("/health")
async def get_audit_health_status():
    """Get the health status of the audit system."""
    from app.api.fourth_estate import get_fourth_estate

    try:
        fourth_estate = get_fourth_estate()
        stats = fourth_estate.get_stats()
        health = fourth_estate.get_health_status()
        
        return {
            "success": True,
            "audit_stats": stats,
            "health_status": health,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}") from e
