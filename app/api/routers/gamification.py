"""EduBoost SA — Gamification Router"""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.services.gamification_service import GamificationService
from app.api.core.database import AsyncSessionFactory


router = APIRouter()


class XPAwardRequest(BaseModel):
    learner_id: UUID
    xp_type: str
    metadata: Optional[dict] = None


class XPAwardResponse(BaseModel):
    success: bool
    xp_awarded: int
    total_xp: int
    level: int
    leveled_up: bool
    new_level: Optional[int] = None
    badges_earned: list = []


class StreakUpdateResponse(BaseModel):
    success: bool
    streak_days: int
    streak_broken: bool
    badges_earned: list = []


class LearnerProfileResponse(BaseModel):
    success: bool
    profile: dict


class LeaderboardResponse(BaseModel):
    success: bool
    leaderboard: list


@router.post("/award-xp", response_model=XPAwardResponse)
async def award_xp(request: XPAwardRequest):
    """Award XP to a learner for completing activities."""
    async with AsyncSessionFactory() as session:
        try:
            service = GamificationService(session)
            result = await service.award_xp(
                learner_id=request.learner_id,
                xp_type=request.xp_type,
                metadata=request.metadata,
            )
            return XPAwardResponse(
                success=True,
                **result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to award XP: {e}") from e


@router.post("/update-streak", response_model=StreakUpdateResponse)
async def update_streak(learner_id: UUID):
    """Update learner streak after activity."""
    async with AsyncSessionFactory() as session:
        try:
            service = GamificationService(session)
            result = await service.update_streak(learner_id)
            return StreakUpdateResponse(
                success=True,
                **result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update streak: {e}") from e


@router.get("/profile/{learner_id}", response_model=LearnerProfileResponse)
async def get_learner_profile(learner_id: UUID):
    """Get learner's gamification profile including XP, level, and badges."""
    async with AsyncSessionFactory() as session:
        try:
            service = GamificationService(session)
            profile = await service.get_learner_profile(learner_id)
            return LearnerProfileResponse(success=True, profile=profile)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get profile: {e}") from e


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(limit: int = Field(default=10, ge=1, le=100)):
    """Get top learners by XP."""
    async with AsyncSessionFactory() as session:
        try:
            service = GamificationService(session)
            leaderboard = await service.get_leaderboard(limit=limit)
            return LeaderboardResponse(success=True, leaderboard=leaderboard)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {e}") from e