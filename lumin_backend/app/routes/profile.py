"""
profiles.py (Routes Layer)

This module defines the Profile API routes.
It is responsible ONLY for:
- Request/response validation (Pydantic)
- Authentication (extract JWT + validate user)
- Authorization (user can only access their own profile)
- Creating a Supabase client authenticated with the user's JWT (for RLS)
- Calling the Facade methods (business logic)

Flow:
Flutter -> FastAPI (/profiles/...) -> validate token -> get Supabase client with JWT
-> Facade -> User domain -> Supabase (DB)
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.supabase_client import supabase, get_supabase_for_jwt
from app.core.lumin_facade import LuminFacade

# Router configuration:
# - prefix="/profiles" means all endpoints start with /profiles
# - tags used for Swagger grouping
router = APIRouter(prefix="/profiles", tags=["profiles"])


# -----------------------------
# Response Model (what API returns)
# -----------------------------
class ProfileOut(BaseModel):
    """
    Profile response payload returned to Flutter.
    Keep it aligned with your `users` table columns (only the fields you need).
    """
    user_id: str
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None

    energy_source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# -----------------------------
# Update Model (what API accepts from Flutter)
# -----------------------------
class ProfileUpdate(BaseModel):
    """
    Fields are optional because we support partial update (PATCH).
    Only provided fields will be updated.
    """
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None

    energy_source: Optional[str] = Field(default=None, description="Grid only or Grid + Solar")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# -----------------------------
# Helpers: Token extraction + user validation
# -----------------------------
def _extract_bearer(authorization: Optional[str]) -> str:
    """
    Extract JWT from Authorization header: "Bearer <token>"

    Why:
    - Standard way for Flutter to send user token
    - Keeps route code clean and consistent
    """
    if not authorization:
        raise HTTPException(401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(401, detail="Invalid Authorization header")

    return parts[1].strip()


def _token_user_id(jwt: str) -> str:
    """
    Validate JWT using Supabase Auth and return user_id (auth.uid()).

    Why:
    - Ensures token is valid
    - Lets us enforce: user can only read/update their own profile (authorization)
    """
    try:
        res = supabase.auth.get_user(jwt)
        user = getattr(res, "user", None)
        if not user or not getattr(user, "id", None):
            raise HTTPException(401, detail="Invalid token")
        return user.id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, detail="Invalid token")


# -----------------------------
# GET /profiles/{user_id}
# -----------------------------
@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(user_id: str, authorization: Optional[str] = Header(default=None)):
    """
    Retrieve the profile for the given user_id.

    Security:
    - Requires Authorization Bearer token
    - Token must belong to the same user_id requested
    - Uses get_supabase_for_jwt(jwt) so RLS policies work correctly
    """
    jwt = _extract_bearer(authorization)
    uid = _token_user_id(jwt)

    # Authorization check: prevent reading someone else's profile
    if uid != user_id:
        raise HTTPException(403, detail="Forbidden")

    # Create Supabase client with JWT so auth.uid() works in RLS
    db = get_supabase_for_jwt(jwt)

    # Facade is the single entrypoint to business logic
    facade = LuminFacade(db)

    try:
        return facade.get_profile(user_id)
    except ValueError:
        # User row not found (or RLS blocked)
        raise HTTPException(404, detail="Profile not found")


# -----------------------------
# PATCH /profiles/{user_id}
# -----------------------------
@router.patch("/{user_id}", response_model=ProfileOut)
def update_profile(
    user_id: str,
    payload: ProfileUpdate,
    authorization: Optional[str] = Header(default=None),
):
    """
    Update profile fields for the given user_id.

    Notes:
    - PATCH means partial update (update only sent fields)
    - exclude_none=True ensures we don't overwrite fields with null unless explicitly sent
    - Authorization rules are the same as GET
    """
    jwt = _extract_bearer(authorization)
    uid = _token_user_id(jwt)

    if uid != user_id:
        raise HTTPException(403, detail="Forbidden")

    db = get_supabase_for_jwt(jwt)
    facade = LuminFacade(db)

    # Convert Pydantic model to dict and remove None values
    info = payload.model_dump(exclude_none=True)

    try:
        return facade.update_profile(user_id, info)
    except Exception as e:
        # Any validation/db error
        raise HTTPException(400, detail=str(e))