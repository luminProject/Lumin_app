from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.supabase_client import supabase, supabase_admin
from app.core.lumin_facade import LuminFacade

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileOut(BaseModel):
    user_id: str
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None
    energy_source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None
    energy_source: Optional[str] = Field(default=None, description="Grid only or Grid + Solar")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(401, detail="Invalid Authorization header")

    return parts[1].strip()


def _token_user_id(jwt: str) -> str:
    try:
        res = supabase.auth.get_user(jwt)
        user = getattr(res, "user", None)
        if not user or not getattr(user, "id", None):
            raise HTTPException(401, detail="Invalid token")
        return str(user.id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, detail="Invalid token")


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(user_id: str, authorization: Optional[str] = Header(default=None)):
    jwt = _extract_bearer(authorization)
    uid = _token_user_id(jwt)

    if uid != user_id:
        raise HTTPException(403, detail="Forbidden")

    # Use admin client here so backend handles auth, not RLS
    facade = LuminFacade(supabase_admin)

    try:
        return facade.get_profile(user_id)
    except ValueError:
        raise HTTPException(404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.patch("/{user_id}", response_model=ProfileOut)
def update_profile(
    user_id: str,
    payload: ProfileUpdate,
    authorization: Optional[str] = Header(default=None),
):
    jwt = _extract_bearer(authorization)
    uid = _token_user_id(jwt)

    if uid != user_id:
        raise HTTPException(403, detail="Forbidden")

    facade = LuminFacade(supabase_admin)
    info = payload.model_dump(exclude_none=True)

    try:
        return facade.update_profile(user_id, info)
    except ValueError:
        raise HTTPException(404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(400, detail=str(e))