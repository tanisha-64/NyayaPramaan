"""Query-log model (synopsis Section 4.6 -- hash-chain audit log)."""
from pydantic import BaseModel
from typing import Optional

class QueryLogEntry(BaseModel):
    query: str
    response: str
    verified: bool
    model_used: Optional[str] = None
    previous_hash: str
    entry_hash: str