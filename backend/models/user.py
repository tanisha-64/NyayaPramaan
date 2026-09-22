"""User/role model (synopsis Section 4.1 -- Auth & RBAC)."""
from pydantic import BaseModel
from enum import Enum

class UserRole(str, Enum):
    professional = "professional"
    public = "public"
    admin = "admin"

class UserProfile(BaseModel):
    id: str
    email: str
    role: UserRole = UserRole.public