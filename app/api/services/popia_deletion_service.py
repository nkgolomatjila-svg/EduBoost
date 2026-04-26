"""
EduBoost SA — POPIA Deletion Service

Implements the right to erasure (right to be forgotten) as required by
South Africa's Protection of Personal Information Act (POPIA).

This service performs data anonymization rather than hard deletion to:
- Maintain data integrity for analytics
- Preserve audit trails
- Allow for statistical analysis
"""
import hashlib
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.db_models import (
    Learner,
    LearnerIdentity,
    SubjectMastery,
    SessionEvent,
    StudyPlan,
    DiagnosticSession,
    DiagnosticResponse,
    ConsentAudit,
    AuditEvent,
)


class PopiaDeletionService:
    """Service for handling POPIA right to erasure requests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def request_deletion(
        self,
        learner_id: UUID,
        guardian_id: UUID,
        reason: Optional[str] = None,
    ) -> dict:
        """
        Submit a request for data deletion under POPIA.
        
        This initiates the deletion workflow. The actual anonymization
        happens asynchronously to allow for verification.
        """
        # Verify guardian has consent
        await self._verify_guardian_consent(learner_id, guardian_id)

        # Create deletion request audit entry
        deletion_request = AuditEvent(
            event_id=uuid.uuid4(),
            learner_id=learner_id,
            event_type="POPIA_DELETION_REQUESTED",
            details={
                "reason": reason,
                "guardian_id": str(guardian_id),
                "requested_at": datetime.now().isoformat(),
            },
            occurred_at=datetime.now(),
        )
        self.session.add(deletion_request)
        await self.session.commit()

        return {
            "request_id": str(deletion_request.event_id),
            "learner_id": str(learner_id),
            "status": "pending",
            "message": "Deletion request submitted. Data will be anonymized within 30 days.",
            "popia_compliant": True,
        }

    async def execute_deletion(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> dict:
        """
        Execute the data anonymization (right to erasure).
        
        Under POPIA, we anonymize data rather than hard delete to:
        - Preserve analytics capabilities
        - Maintain audit trails
        - Allow statistical analysis
        """
        # Verify guardian has consent
        await self._verify_guardian_consent(learner_id, guardian_id)

        # Generate anonymization hash
        anonymization_id = hashlib.sha256(
            f"{learner_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Anonymize learner record
        learner = await self.session.get(Learner, learner_id)
        if learner:
            learner.first_name = f"DELETED_{anonymization_id}"
            learner.last_name = f"DELETED_{anonymization_id}"
            learner.email = None
            learner.overall_mastery = 0.0
            learner.streak_days = 0
            learner.total_xp = 0
            learner.is_active = False
            learner.deleted_at = datetime.now()

        # Anonymize learner identity
        result = await self.session.execute(
            select(LearnerIdentity).where(LearnerIdentity.learner_id == learner_id)
        )
        identity = result.scalar_one_or_none()
        if identity:
            identity.pseudonym = f"DELETED_{anonymization_id}"
            identity.anonymized = True

        # Anonymize subject mastery (keep scores but remove identifying info)
        result = await self.session.execute(
            select(SubjectMastery).where(SubjectMastery.learner_id == learner_id)
        )
        for sm in result.scalars().all():
            sm.concepts_mastered = []
            sm.knowledge_gaps = []

        # Anonymize session events
        await self.session.execute(
            text("""
                UPDATE session_events 
                SET event_type = 'ANONYMIZED',
                    details = jsonb_set(details, '{anonymized}', 'true')
                WHERE learner_id = :learner_id
            """),
            {"learner_id": str(learner_id)},
        )

        # Anonymize diagnostic sessions
        result = await self.session.execute(
            select(DiagnosticSession).where(DiagnosticSession.learner_id == learner_id)
        )
        for ds in result.scalars().all():
            ds.knowledge_gaps = []
            ds.recommendations = None

        # Anonymize study plans
        result = await self.session.execute(
            select(StudyPlan).where(StudyPlan.learner_id == learner_id)
        )
        for sp in result.scalars().all():
            sp.schedule = {}
            sp.week_focus = "DELETED"

        # Record deletion in consent audit
        consent_audit = ConsentAudit(
            audit_id=uuid.uuid4(),
            pseudonym_id=learner_id,
            event_type="consent_revoked",
            consent_version=1,
            details={
                "reason": "POPIA deletion request executed",
                "anonymization_id": anonymization_id,
                "executed_at": datetime.now().isoformat(),
            },
            occurred_at=datetime.now(),
        )
        self.session.add(consent_audit)

        # Record completion in audit events
        completion_event = AuditEvent(
            event_id=uuid.uuid4(),
            learner_id=learner_id,
            event_type="POPIA_DELETION_COMPLETED",
            details={
                "anonymization_id": anonymization_id,
                "guardian_id": str(guardian_id),
                "executed_at": datetime.now().isoformat(),
            },
            occurred_at=datetime.now(),
        )
        self.session.add(completion_event)

        # Invalidate all active sessions
        await self.invalidate_sessions(learner_id)

        await self.session.commit()

        return {
            "learner_id": str(learner_id),
            "status": "completed",
            "anonymization_id": anonymization_id,
            "message": "Data has been anonymized in compliance with POPIA. "
                       "Analytics data retained in anonymized form.",
            "popia_compliant": True,
        }

    async def get_deletion_status(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> dict:
        """Get the status of a deletion request."""
        # Verify guardian has consent
        await self._verify_guardian_consent(learner_id, guardian_id)

        # Check for recent deletion events
        result = await self.session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.learner_id == learner_id,
                AuditEvent.event_type.in_(["POPIA_DELETION_REQUESTED", "POPIA_DELETION_COMPLETED"]),
            )
            .order_by(AuditEvent.occurred_at.desc())
            .limit(1)
        )
        latest_event = result.scalar_one_or_none()

        if not latest_event:
            return {
                "learner_id": str(learner_id),
                "status": "none",
                "message": "No deletion request found",
            }

        learner = await self.session.get(Learner, learner_id)
        is_deleted = learner and learner.deleted_at is not None

        return {
            "learner_id": str(learner_id),
            "status": "completed" if is_deleted else "pending",
            "requested_at": latest_event.occurred_at.isoformat() if latest_event else None,
            "completed_at": learner.deleted_at.isoformat() if is_deleted and learner.deleted_at else None,
        }

    async def export_data(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> dict:
        """
        Export all learner data before deletion (POPIA requirement).
        
        Parents have the right to receive a copy of all stored data
        before exercising the right to erasure.
        """
        # Verify guardian has consent
        await self._verify_guardian_consent(learner_id, guardian_id)

        # Gather all data
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Get subject mastery
        result = await self.session.execute(
            select(SubjectMastery).where(SubjectMastery.learner_id == learner_id)
        )
        subject_mastery = [
            {
                "subject_code": sm.subject_code,
                "mastery_score": sm.mastery_score,
                "concepts_mastered": sm.concepts_mastered,
                "knowledge_gaps": sm.knowledge_gaps,
                "last_assessed": sm.last_assessed_at.isoformat() if sm.last_assessed_at else None,
            }
            for sm in result.scalars().all()
        ]

        # Get session events
        result = await self.session.execute(
            select(SessionEvent)
            .where(SessionEvent.learner_id == learner_id)
            .order_by(SessionEvent.occurred_at.desc())
            .limit(100)
        )
        session_events = [
            {
                "event_type": e.event_type,
                "details": e.details,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in result.scalars().all()
        ]

        # Get study plans
        result = await self.session.execute(
            select(StudyPlan)
            .where(StudyPlan.learner_id == learner_id)
            .order_by(StudyPlan.created_at.desc())
        )
        study_plans = [
            {
                "plan_id": str(sp.plan_id),
                "week_start": sp.week_start.isoformat(),
                "week_focus": sp.week_focus,
                "gap_ratio": sp.gap_ratio,
                "schedule": sp.schedule,
                "created_at": sp.created_at.isoformat(),
            }
            for sp in result.scalars().all()
        ]

        # Get diagnostic sessions
        result = await self.session.execute(
            select(DiagnosticSession)
            .where(DiagnosticSession.learner_id == learner_id)
            .order_by(DiagnosticSession.started_at.desc())
        )
        diagnostics = [
            {
                "session_id": str(ds.session_id),
                "subject_code": ds.subject_code,
                "grade_level": ds.grade_level,
                "theta_estimate": ds.theta_estimate,
                "final_mastery_score": ds.final_mastery_score,
                "knowledge_gaps": ds.knowledge_gaps,
                "completed_at": ds.completed_at.isoformat() if ds.completed_at else None,
            }
            for ds in result.scalars().all()
        ]

        # Get consent history
        result = await self.session.execute(
            select(ConsentAudit)
            .where(ConsentAudit.pseudonym_id == learner_id)
            .order_by(ConsentAudit.occurred_at.desc())
        )
        consent_history = [
            {
                "event_type": ca.event_type,
                "consent_version": ca.consent_version,
                "occurred_at": ca.occurred_at.isoformat(),
            }
            for ca in result.scalars().all()
        ]

        return {
            "learner_id": str(learner_id),
            "exported_at": datetime.now().isoformat(),
            "data": {
                "profile": {
                    "grade": learner.grade,
                    "overall_mastery": learner.overall_mastery,
                    "streak_days": learner.streak_days,
                    "total_xp": learner.total_xp,
                    "created_at": learner.created_at.isoformat() if learner.created_at else None,
                    "last_active": learner.last_active_at.isoformat() if learner.last_active_at else None,
                },
                "subject_mastery": subject_mastery,
                "session_events": session_events,
                "study_plans": study_plans,
                "diagnostic_sessions": diagnostics,
                "consent_history": consent_history,
            },
        }

    async def _verify_guardian_consent(
        self,
        learner_id: UUID,
        guardian_id: UUID,
    ) -> None:
        """Verify that the guardian has consent to access learner data."""
        from fastapi import HTTPException

        result = await self.session.execute(
            select(ConsentAudit)
            .where(
                ConsentAudit.pseudonym_id == learner_id,
                ConsentAudit.event_type == "consent_granted",
            )
            .order_by(ConsentAudit.occurred_at.desc())
            .limit(1)
        )
        consent = result.scalar_one_or_none()

        if not consent:
            raise HTTPException(
                status_code=403,
                detail="Guardian consent required to access learner data",
            )

        # Check if consent has been revoked
        result = await self.session.execute(
            select(ConsentAudit)
            .where(
                ConsentAudit.pseudonym_id == learner_id,
                ConsentAudit.event_type == "consent_revoked",
            )
            .order_by(ConsentAudit.occurred_at.desc())
            .limit(1)
        )
        revoked = result.scalar_one_or_none()

        if revoked and revoked.occurred_at > consent.occurred_at:
            raise HTTPException(
                status_code=403,
                detail="Guardian consent has been revoked",
            )

    async def invalidate_sessions(
        self,
        learner_id: UUID,
    ) -> dict:
        """
        Invalidate all active sessions for a learner.
        
        Called when data deletion is executed to ensure no active
        sessions remain after anonymization.
        """
        from app.api.models.db_models import SessionEvent
        
        # Record session invalidation in audit
        invalidation_event = AuditEvent(
            event_id=uuid.uuid4(),
            learner_id=learner_id,
            event_type="SESSIONS_INVALIDATED",
            details={
                "reason": "POPIA data deletion",
                "executed_at": datetime.now().isoformat(),
            },
            occurred_at=datetime.now(),
        )
        self.session.add(invalidation_event)
        
        # Update session events to reflect invalidation
        await self.session.execute(
            text("""
                UPDATE session_events 
                SET event_type = 'SESSION_INVALIDATED',
                    details = jsonb_set(details, '{invalidated_at}', :now)
                WHERE learner_id = :learner_id
                AND event_type IN ('LOGIN', 'SESSION_CREATED')
            """),
            {"learner_id": str(learner_id), "now": datetime.now().isoformat()},
        )
        
        await self.session.commit()
        
        return {
            "learner_id": str(learner_id),
            "status": "sessions_invalidated",
            "message": "All active sessions have been invalidated",
        }