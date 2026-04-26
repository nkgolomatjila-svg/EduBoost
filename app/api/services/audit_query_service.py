"""
EduBoost SA — Audit Query and Search Service

Provides functionality to query, search, and filter audit events
for compliance and transparency purposes.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.db_models import AuditEvent


class AuditEventType(str, Enum):
    """Types of audit events to filter on."""
    ACTION_SUBMITTED = "ACTION_SUBMITTED"
    STAMP_ISSUED = "STAMP_ISSUED"
    STAMP_REJECTED = "STAMP_REJECTED"
    CONSTITUTIONAL_VIOL = "CONSTITUTIONAL_VIOL"
    LLM_CALL_COMPLETED = "LLM_CALL_COMPLETED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"
    CONSENT_RECORDED = "CONSENT_RECORDED"
    DATA_ACCESSED = "DATA_ACCESSED"
    DATA_MODIFIED = "DATA_MODIFIED"
    DELETION_REQUESTED = "DELETION_REQUESTED"
    DELETION_EXECUTED = "DELETION_EXECUTED"


class AuditPillar(str, Enum):
    """Constitutional pillars for audit filtering."""
    LEGISLATURE = "LEGISLATURE"
    EXECUTIVE = "EXECUTIVE"
    JUDICIARY = "JUDICIARY"
    FOURTH_ESTATE = "FOURTH_ESTATE"
    ETHER = "ETHER"


class AuditQueryService:
    """Service for querying and searching audit events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def query_events(
        self,
        learner_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        pillar: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Query audit events with optional filtering.
        
        Args:
            learner_id: Filter by learner (pseudonymous hash)
            event_type: Filter by event type
            pillar: Filter by constitutional pillar
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            Dictionary with events and metadata
        """
        conditions = []

        if learner_id:
            conditions.append(AuditEvent.learner_hash == str(learner_id))
        
        if event_type:
            conditions.append(AuditEvent.event_type == event_type)
        
        if pillar:
            conditions.append(AuditEvent.pillar == pillar)
        
        if start_date:
            conditions.append(AuditEvent.occurred_at >= start_date)
        
        if end_date:
            conditions.append(AuditEvent.occurred_at <= end_date)

        # Build query
        query = select(AuditEvent)
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by date descending (most recent first)
        query = query.order_by(AuditEvent.occurred_at.desc())
        
        # Add pagination
        total_query = select(AuditEvent)
        if conditions:
            total_query = total_query.where(and_(*conditions))

        # Get total count
        result = await self.session.execute(select(AuditEvent).where(and_(*conditions)) if conditions else select(AuditEvent))
        total_count = len(result.scalars().all())

        # Get paginated results
        result = await self.session.execute(
            query.offset(offset).limit(limit)
        )
        events = result.scalars().all()

        return {
            "total": total_count,
            "offset": offset,
            "limit": limit,
            "count": len(events),
            "events": [
                {
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                    "pillar": event.pillar,
                    "learner_hash": event.learner_hash,
                    "action_id": event.action_id,
                    "payload": event.payload,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in events
            ],
        }

    async def search_events(
        self,
        query: str,
        learner_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> dict:
        """
        Free-text search for audit events.
        
        Searches in event type and payload fields.
        """
        # Get all events for this learner or all events
        if learner_id:
            result = await self.session.execute(
                select(AuditEvent).where(AuditEvent.learner_hash == str(learner_id))
            )
        else:
            result = await self.session.execute(select(AuditEvent))
        
        all_events = result.scalars().all()

        # Filter by search query (case-insensitive)
        query_lower = query.lower()
        matching_events = []

        for event in all_events:
            # Search in event_type
            if query_lower in event.event_type.lower():
                matching_events.append(event)
            # Search in pillar
            elif query_lower in event.pillar.lower():
                matching_events.append(event)
            # Search in payload (as string)
            elif event.payload and query_lower in str(event.payload).lower():
                matching_events.append(event)

        # Sort by date descending
        matching_events.sort(key=lambda e: e.occurred_at, reverse=True)

        # Apply limit
        matching_events = matching_events[:limit]

        return {
            "search_query": query,
            "total_matches": len(matching_events),
            "limit": limit,
            "events": [
                {
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                    "pillar": event.pillar,
                    "learner_hash": event.learner_hash,
                    "payload": event.payload,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in matching_events
            ],
        }

    async def get_learner_audit_trail(
        self,
        learner_id: UUID,
        days: int = 30,
    ) -> dict:
        """
        Get complete audit trail for a learner over a time period.
        
        Useful for POPIA compliance audits and parent reviews.
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        result = await self.session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.learner_hash == str(learner_id),
                AuditEvent.occurred_at >= cutoff_date,
            )
            .order_by(AuditEvent.occurred_at.asc())
        )
        events = result.scalars().all()

        # Organize by category
        categorized = {
            "access": [],
            "modifications": [],
            "consent": [],
            "deletions": [],
            "violations": [],
            "other": [],
        }

        for event in events:
            event_dict = {
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "pillar": event.pillar,
                "payload": event.payload,
                "occurred_at": event.occurred_at.isoformat(),
            }

            if "ACCESS" in event.event_type or "READ" in event.event_type:
                categorized["access"].append(event_dict)
            elif "MODIFIED" in event.event_type or "WRITTEN" in event.event_type:
                categorized["modifications"].append(event_dict)
            elif "CONSENT" in event.event_type:
                categorized["consent"].append(event_dict)
            elif "DELETION" in event.event_type:
                categorized["deletions"].append(event_dict)
            elif "VIOL" in event.event_type or "REJECTED" in event.event_type:
                categorized["violations"].append(event_dict)
            else:
                categorized["other"].append(event_dict)

        return {
            "learner_id": str(learner_id),
            "period_days": days,
            "total_events": len(events),
            "events_by_category": categorized,
            "summary": {
                "access_count": len(categorized["access"]),
                "modification_count": len(categorized["modifications"]),
                "consent_records": len(categorized["consent"]),
                "deletion_records": len(categorized["deletions"]),
                "violations": len(categorized["violations"]),
            },
        }

    async def get_compliance_report(
        self,
        days: int = 90,
    ) -> dict:
        """
        Generate a compliance report from audit events.
        
        Provides statistics on constitutional adherence, rejections, violations.
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Get all events in period
        result = await self.session.execute(
            select(AuditEvent).where(AuditEvent.occurred_at >= cutoff_date)
        )
        all_events = result.scalars().all()

        # Calculate statistics
        total_events = len(all_events)
        
        # Count by event type
        event_counts = {}
        for event in all_events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1

        # Count by pillar
        pillar_counts = {}
        for event in all_events:
            pillar_counts[event.pillar] = pillar_counts.get(event.pillar, 0) + 1

        # Count violations
        violation_count = event_counts.get("CONSTITUTIONAL_VIOL", 0)
        rejection_count = event_counts.get("STAMP_REJECTED", 0)

        # Count successful vs failed LLM calls
        llm_success = event_counts.get("LLM_CALL_COMPLETED", 0)
        llm_failed = event_counts.get("LLM_CALL_FAILED", 0)
        llm_total = llm_success + llm_failed
        llm_success_rate = (llm_success / llm_total * 100) if llm_total > 0 else 0

        # Count unique learners affected
        result = await self.session.execute(
            select(AuditEvent.learner_hash)
            .where(AuditEvent.occurred_at >= cutoff_date)
            .distinct()
        )
        unique_learners = len(result.scalars().all())

        return {
            "report_period_days": days,
            "report_generated_at": datetime.now().isoformat(),
            "total_events": total_events,
            "unique_learners": unique_learners,
            "constitutional_health": {
                "violations_count": violation_count,
                "rejections_count": rejection_count,
                "approval_rate": ((total_events - rejection_count) / total_events * 100) if total_events > 0 else 0,
            },
            "llm_performance": {
                "total_calls": llm_total,
                "successful": llm_success,
                "failed": llm_failed,
                "success_rate": llm_success_rate,
            },
            "event_distribution": event_counts,
            "pillar_distribution": pillar_counts,
            "recommendations": self._generate_recommendations(
                violation_count=violation_count,
                rejection_count=rejection_count,
                llm_success_rate=llm_success_rate,
            ),
        }

    def _generate_recommendations(
        self,
        violation_count: int,
        rejection_count: int,
        llm_success_rate: float,
    ) -> list[str]:
        """Generate recommendations based on compliance metrics."""
        recommendations = []

        if violation_count > 5:
            recommendations.append("High constitutional violations detected. Review judiciary rules and data handling practices.")
        
        if rejection_count > total_events * 0.1:
            recommendations.append("High request rejection rate. Review action submissions for policy compliance.")
        
        if llm_success_rate < 95:
            recommendations.append("LLM call failure rate is concerning. Investigate inference gateway stability.")
        
        if not recommendations:
            recommendations.append("Audit trail shows good compliance. Continue current practices.")

        return recommendations
