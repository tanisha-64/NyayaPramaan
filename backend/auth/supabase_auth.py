"""
Auth & RBAC (synopsis Section 4.1 -- API Gateway & Auth)
Verifies Supabase-issued JWT tokens and extracts the user's role.
"""
from supabase import create_client
from fastapi import Header, HTTPException
import os
from dotenv import load_dotenv

load_dotenv()


def get_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def get_current_user(authorization: str = Header(None)):
    """
    Dependency for protected routes. Frontend sends:
    Authorization: Bearer <supabase-access-token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    client = get_client()
    try:
        user_response = client.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="User not found")
        return user_response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_optional_user(authorization: str = Header(None)):
    """
    Optional dependency: returns user if valid Bearer token provided, None otherwise.
    Does NOT throw 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]
    client = get_client()
    try:
        user_response = client.auth.get_user(token)
        return user_response.user
    except Exception:
        return None


def get_admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "mitanisha74@gmail.com")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def get_user_effective_role(user) -> str:
    """
    Returns effective role: 'admin', 'professional', or 'public'.
    Strictly verifies that ONLY whitelisted admin email addresses can have the 'admin' role.
    """
    user_email = (getattr(user, "email", None) or "").strip().lower()
    if user_email and user_email in get_admin_emails():
        return "admin"

    user_meta = getattr(user, "user_metadata", {}) or {}
    role = user_meta.get("role", "public")
    if role == "admin":
        return "public"  # Block unauthorized admin escalation attempts
    return role if role in ["public", "professional"] else "public"


def require_role(user, allowed_roles: list[str]):
    """
    Checks user role against an allow-list.
    Super Admin (mitanisha74@gmail.com) is granted unrestricted access across all endpoints.
    Other users can only access their authorized roles (public or professional).
    """
    user_email = (getattr(user, "email", None) or "").strip().lower()
    if user_email and user_email in get_admin_emails():
        return "admin"

    role = get_user_effective_role(user)
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Role '{role}' not permitted for this action")
    return role
