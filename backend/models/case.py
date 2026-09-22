"""Case model (synopsis Section 4.2 -- Case Management)."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CaseCreate(BaseModel):
    case_text: str

class CaseResponse(BaseModel):
    id: str
    case_text: str
    summary: Optional[str] = None
    timeline: Optional[str] = None
    created_at: Optional[datetime] = None