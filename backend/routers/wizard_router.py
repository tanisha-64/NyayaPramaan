"""Procedure Wizards -> backend/routers/wizard_router.py
Static guided step-by-step flows (FIR refusal, bail, cheque bounce, scam check). The branching logic
lives entirely in wizard_definitions.py and is walked client-side; this router only serves that data
and does the one real computation -- the cheque-bounce deadline dates."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.wizards.wizard_definitions import WIZARDS
from backend.auth.supabase_auth import get_current_user

router = APIRouter()


@router.get("/list")
def list_wizards(user=Depends(get_current_user)):
    return [{"id": wid, "title": w["title"], "icon": w["icon"]} for wid, w in WIZARDS.items()]


@router.get("/{wizard_id}")
def get_wizard(wizard_id: str, user=Depends(get_current_user)):
    wizard = WIZARDS.get(wizard_id)
    if not wizard:
        raise HTTPException(status_code=404, detail="Wizard not found")
    return wizard


class ChequeBounceDeadlineRequest(BaseModel):
    bounce_date: date


@router.post("/cheque-bounce/deadline")
def cheque_bounce_deadline(body: ChequeBounceDeadlineRequest, user=Depends(get_current_user)):
    notice_deadline = body.bounce_date + timedelta(days=30)
    payment_window_ends = notice_deadline + timedelta(days=15)
    complaint_deadline = payment_window_ends + timedelta(days=30)
    return {
        "bounce_date": body.bounce_date.isoformat(),
        "notice_deadline": notice_deadline.isoformat(),
        "payment_window_ends": payment_window_ends.isoformat(),
        "complaint_deadline": complaint_deadline.isoformat(),
    }