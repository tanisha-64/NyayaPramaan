
"""

Auth & RBAC — verifies Supabase-issued JWT tokens.

"""

from supabase import create_client

from fastapi import Header, HTTPException

import os

from dotenv import load_dotenv



load_dotenv()





def get_client():

    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])





def get_current_user(authorization: str = Header(None)):

    if not authorization or not authorization.startswith("Bearer "):

        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]

    client = get_client()

    try:

        user_response = client.auth.get_user(token)

        return user_response.user

    except Exception:

        raise HTTPException(status_code=401, detail="Invalid or expired token")





def require_role(user, allowed_roles: list[str]):

    role = (user.user_metadata or {}).get("role", "public")

    if role not in allowed_roles:

        raise HTTPException(status_code=403, detail=f"Role '{role}' not permitted for this action")

    return role

