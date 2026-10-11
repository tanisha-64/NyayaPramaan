"""
Auth & RBAC — verifies Supabase-issued JWT tokens and extracts the user's role.
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


_DEFAULT_ADMIN_EMAILS = "mitanisha74@gmail.com"


def get_admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS")
    if raw is None:
        # Legacy fallback kept so a missing env var does not silently lock the owner out. Set ADMIN_EMAILS in
        # production so admin access is explicit configuration, not a value baked into source.
        print("[auth] ADMIN_EMAILS is not set; using the built-in default admin list")
        raw = _DEFAULT_ADMIN_EMAILS
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def get_user_effective_role(user) -> str:
    """
    Returns effective role: 'admin', 'professional', or 'public'.

    'admin' requires BOTH a whitelisted email AND a confirmed email address. Without the confirmation check, anyone
    could register the admin address on a project that allows unconfirmed sign-ups and be treated as admin.
    user_metadata is writable by the user themself, so it can never grant 'admin'; 'professional' is
    informational only and confers no privileges.
    """
    user_email = (getattr(user, "email", None) or "").strip().lower()
    email_confirmed = bool(getattr(user, "email_confirmed_at", None) or getattr(user, "confirmed_at", None))
    if user_email and email_confirmed and user_email in get_admin_emails():
        return "admin"

    user_meta = getattr(user, "user_metadata", {}) or {}
    role = user_meta.get("role", "public")
    return role if role == "professional" else "public"


def require_role(user, allowed_roles: list[str]):
    role = get_user_effective_role(user)
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
    return role
