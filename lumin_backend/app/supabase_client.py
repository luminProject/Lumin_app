import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ---- Basic validation ----
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE credentials")

# ---- Normal client (respects RLS) ----
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Admin client (bypasses RLS) ----
if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# =============================
# AUTH HELPERS
# =============================
def get_supabase_for_jwt(jwt: str):
    """
    Create a Supabase client authenticated with user JWT.

    Used when you want RLS to apply per user.
    """

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(jwt)
    return client
def extract_bearer(authorization: Optional[str]) -> str:
    """
    Extract JWT from Authorization header.
    Expected format:
    Authorization: Bearer <token>
    """

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    return parts[1].strip()


def get_token_user_id(jwt: str) -> str:
    """
    Decode JWT and return user_id.

    Used to:
    - verify user identity
    """

    try:
        res = supabase.auth.get_user(jwt)
        user = getattr(res, "user", None)

        if not user or not getattr(user, "id", None):
            raise HTTPException(status_code=401, detail="Invalid token")

        return str(user.id)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_user_access(
    user_id: str,
    authorization: Optional[str],
) -> str:
    """
    Ensure user can only access their own data.

    Steps:
    1. Extract JWT
    2. Decode user_id
    3. Compare with requested user_id
    """

    jwt = extract_bearer(authorization)
    token_user_id = get_token_user_id(jwt)

    if token_user_id != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    return token_user_id