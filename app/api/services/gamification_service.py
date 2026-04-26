"""
EduBoost SA — Gamification Service

Handles XP calculation, badge awards, streak tracking, and
progression mechanics for Grade R-3 and Grade 4-7 modes.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.db_models import Learner, LearnerBadge, Badge


# XP Configuration
XP_CONFIG = {
    "lesson_complete": 35,
    "lesson_mastery": 50,
    "diagnostic_complete": 25,
    "perfect_score": 20,
    "streak_bonus": 5,  # Per day of streak
    "daily_login": 10,
    "badge_earned": 100,
    "concept_mastered": 15,
    "study_plan_complete": 30,
}

# Streak thresholds
STREAK_THRESHOLDS = [3, 7, 14, 30, 60, 100]

# Grade band configurations
GRADE_BAND_CONFIG = {
    "R-3": {
        "badge_types": ["streak", "mastery", "milestone"],
        "engagement_style": "rewards",  # XP, badges, streaks
        "max_daily_xp": 200,
    },
    "4-7": {
        "badge_types": ["discovery", "mastery", "milestone"],
        "engagement_style": "discovery",  # Unlockables, achievements
        "max_daily_xp": 250,
    },
}


class GamificationService:
    """Service for managing learner gamification mechanics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_learner_profile(self, learner_id: UUID) -> dict:
        """Get the learner's gamification profile."""
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Get earned badges
        result = await self.session.execute(
            select(LearnerBadge, Badge)
            .join(Badge, LearnerBadge.badge_id == Badge.badge_id)
            .where(LearnerBadge.learner_id == learner_id)
        )
        earned_badges = []
        for lb, badge in result.all():
            earned_badges.append({
                "badge_id": str(badge.badge_id),
                "badge_key": badge.badge_key,
                "name": badge.name,
                "description": badge.description,
                "icon_url": badge.icon_url,
                "earned_at": lb.earned_at.isoformat(),
            })

        # Determine grade band
        grade_band = "R-3" if learner.grade <= 3 else "4-7"

        return {
            "learner_id": str(learner.learner_id),
            "grade": learner.grade,
            "grade_band": grade_band,
            "total_xp": learner.total_xp,
            "streak_days": learner.streak_days,
            "level": self._calculate_level(learner.total_xp),
            "xp_to_next_level": self._xp_to_next_level(learner.total_xp),
            "badges": earned_badges,
            "can_earn_badges": self._get_available_badges(learner.grade),
        }

    def _calculate_level(self, total_xp: int) -> int:
        """Calculate level from total XP (100 XP per level)."""
        return max(1, (total_xp // 100) + 1)

    def _xp_to_next_level(self, total_xp: int) -> int:
        """Calculate XP needed for next level."""
        current_level = self._calculate_level(total_xp)
        xp_for_next = current_level * 100
        return max(0, xp_for_next - total_xp)

    def _get_available_badges(self, grade: int) -> list[dict]:
        """Get badges available for the learner's grade."""
        grade_band = "R-3" if grade <= 3 else "4-7"
        config = GRADE_BAND_CONFIG[grade_band]

        # Return badge templates based on grade band
        badges = []
        for badge_type in config["badge_types"]:
            if badge_type == "streak":
                for threshold in STREAK_THRESHOLDS:
                    badges.append({
                        "badge_key": f"streak_{threshold}",
                        "name": f"{threshold}-Day Streak",
                        "description": f"Complete lessons for {threshold} consecutive days",
                        "badge_type": "streak",
                        "threshold": threshold,
                    })
            elif badge_type == "mastery":
                badges.extend([
                    {"badge_key": "mastery_5", "name": "Quick Learner", "description": "Master 5 concepts", "badge_type": "mastery", "threshold": 5},
                    {"badge_key": "mastery_10", "name": "Knowledge Seeker", "description": "Master 10 concepts", "badge_type": "mastery", "threshold": 10},
                    {"badge_key": "mastery_25", "name": "Subject Expert", "description": "Master 25 concepts", "badge_type": "mastery", "threshold": 25},
                ])
            elif badge_type == "milestone":
                badges.extend([
                    {"badge_key": "first_lesson", "name": "First Steps", "description": "Complete your first lesson", "badge_type": "milestone", "threshold": 1},
                    {"badge_key": "lessons_10", "name": "Dedicated Learner", "description": "Complete 10 lessons", "badge_type": "milestone", "threshold": 10},
                    {"badge_key": "lessons_50", "name": "Scholar", "description": "Complete 50 lessons", "badge_type": "milestone", "threshold": 50},
                ])
            elif badge_type == "discovery":
                badges.extend([
                    {"badge_key": "discovery_math", "name": "Math Explorer", "description": "Explore 5 different math topics", "badge_type": "discovery", "threshold": 5},
                    {"badge_key": "discovery_science", "name": "Science Explorer", "description": "Explore 5 different science topics", "badge_type": "discovery", "threshold": 5},
                ])

        return badges

    async def award_xp(
        self,
        learner_id: UUID,
        xp_type: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Award XP to a learner and check for level-ups.
        
        Args:
            learner_id: The learner's UUID
            xp_type: Type of XP award (lesson_complete, streak_bonus, etc.)
            metadata: Additional context for the XP award
        
        Returns:
            Dict with XP awarded and any level-up info
        """
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Get XP amount
        xp_amount = XP_CONFIG.get(xp_type, 0)
        if xp_amount == 0:
            raise ValueError(f"Unknown XP type: {xp_type}")

        # Apply streak bonus if applicable
        if xp_type == "lesson_complete" and learner.streak_days > 0:
            streak_bonus = min(learner.streak_days * XP_CONFIG["streak_bonus"], 25)
            xp_amount += streak_bonus

        # Check daily XP cap
        grade_band = "R-3" if learner.grade <= 3 else "4-7"
        max_daily = GRADE_BAND_CONFIG[grade_band]["max_daily_xp"]

        # Update learner XP
        old_level = self._calculate_level(learner.total_xp)
        learner.total_xp += xp_amount
        new_level = self._calculate_level(learner.total_xp)

        await self.session.commit()

        result = {
            "xp_awarded": xp_amount,
            "total_xp": learner.total_xp,
            "level": new_level,
            "leveled_up": new_level > old_level,
        }

        if result["leveled_up"]:
            result["new_level"] = new_level

        # Check for badge awards
        badges_earned = await self._check_badge_awards(learner)
        if badges_earned:
            result["badges_earned"] = badges_earned

        return result

    async def update_streak(self, learner_id: UUID) -> dict:
        """
        Update learner streak based on activity.
        
        Should be called when learner completes a lesson or logs in.
        """
        learner = await self.session.get(Learner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        now = datetime.now()
        last_active = learner.last_active_at

        # Check if streak should continue or reset
        if last_active is None:
            # First activity
            learner.streak_days = 1
        else:
            days_since_active = (now.date() - last_active.date()).days

            if days_since_active == 0:
                # Same day, no change
                pass
            elif days_since_active == 1:
                # Consecutive day, increment streak
                learner.streak_days += 1
            else:
                # Streak broken, reset to 1
                learner.streak_days = 1

        # Update last active
        learner.last_active_at = now

        await self.session.commit()

        # Check for streak badges
        badges_earned = await self._check_streak_badges(learner)

        return {
            "streak_days": learner.streak_days,
            "streak_broken": days_since_active > 1 if last_active else False,
            "badges_earned": badges_earned,
        }

    async def _check_badge_awards(self, learner: Learner) -> list[dict]:
        """Check and award any earned badges."""
        earned_badges = []

        # Get existing badges for learner
        result = await self.session.execute(
            select(LearnerBadge.badge_id).where(LearnerBadge.learner_id == learner.learner_id)
        )
        existing_badges = {row[0] for row in result.all()}

        # Check streak badges
        for threshold in STREAK_THRESHOLDS:
            if learner.streak_days >= threshold:
                badge_key = f"streak_{threshold}"
                badge = await self._get_or_create_badge(
                    badge_key=badge_key,
                    name=f"{threshold}-Day Streak",
                    description=f"Complete lessons for {threshold} consecutive days",
                    badge_type="streak",
                    threshold=threshold,
                    grade_band="R-3" if learner.grade <= 3 else "4-7",
                )
                if badge and badge.badge_id not in existing_badges:
                    await self._award_badge(learner.learner_id, badge.badge_id)
                    earned_badges.append({
                        "badge_key": badge_key,
                        "name": badge.name,
                    })

        return earned_badges

    async def _check_streak_badges(self, learner: Learner) -> list[dict]:
        """Check and award streak-based badges."""
        return await self._check_badge_awards(learner)

    async def _get_or_create_badge(
        self,
        badge_key: str,
        name: str,
        description: str,
        badge_type: str,
        threshold: int,
        grade_band: str,
    ) -> Optional[Badge]:
        """Get existing badge or create new one."""
        result = await self.session.execute(
            select(Badge).where(Badge.badge_key == badge_key)
        )
        badge = result.scalar_one_or_none()

        if not badge:
            badge = Badge(
                badge_id=uuid.uuid4(),
                badge_key=badge_key,
                name=name,
                description=description,
                badge_type=badge_type,
                threshold=threshold,
                grade_band=grade_band,
                xp_value=XP_CONFIG["badge_earned"],
            )
            self.session.add(badge)
            await self.session.commit()
            await self.session.refresh(badge)

        return badge

    async def _award_badge(self, learner_id: UUID, badge_id: UUID) -> None:
        """Award a badge to a learner."""
        learner_badge = LearnerBadge(
            id=uuid.uuid4(),
            learner_id=learner_id,
            badge_id=badge_id,
        )
        self.session.add(learner_badge)
        await self.session.commit()

    async def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """Get top learners by XP."""
        result = await self.session.execute(
            select(Learner)
            .order_by(Learner.total_xp.desc())
            .limit(limit)
        )
        learners = result.scalars().all()

        leaderboard = []
        for rank, learner in enumerate(learners, 1):
            leaderboard.append({
                "rank": rank,
                "learner_id": str(learner.learner_id),
                "grade": learner.grade,
                "total_xp": learner.total_xp,
                "streak_days": learner.streak_days,
                "level": self._calculate_level(learner.total_xp),
            })

        return leaderboard