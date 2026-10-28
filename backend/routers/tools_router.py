"""backend/routers/tools_router.py (NEW). Register in main.py:
    from backend.routers import tools_router
    app.include_router(tools_router.router, prefix="/tools", tags=["tools"])"""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ai_core.rag.cheque_deadlines import QUICK_FACTS, compute
from ai_core.rag.legal_scope import scope_info
from backend.auth.supabase_auth import get_current_user

router = APIRouter()


class ChequeIn(BaseModel):
    cheque_date: date = Field(..., description="Cheque par likhi tareekh")
    bank_info_date: date = Field(..., description="Jis din bank se bounce/return ki jaankari mili")
    presented_date: date | None = None
    notice_sent_date: date | None = None
    notice_received_date: date | None = None
    validity_months: int = Field(3, ge=1, le=6)


@router.post("/cheque-deadlines")
def cheque_deadlines(body: ChequeIn, user=Depends(get_current_user)):
    out = compute(body.cheque_date, body.bank_info_date, body.presented_date, body.notice_sent_date,
                  body.notice_received_date, body.validity_months)
    return {**out, "facts": QUICK_FACTS, "source": "Negotiable Instruments Act, 1881 - s.138, 142 (India Code)",
            "disclaimer": "Yeh tool tareekhon ka anumaan deta hai, kanooni salah nahi. Vakil se confirm karein."}


@router.get("/scope")
def get_scope(user=Depends(get_current_user)):
    """Returns supported topics and example questions for the welcome screen."""
    return scope_info()