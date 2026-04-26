from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "EduBoost SA API", "timestamp": datetime.utcnow().isoformat()}


@router.get("/")
async def root():
    return {"message": "🦁 EduBoost SA API — Yebo! We are live.", "docs": "/docs"}
