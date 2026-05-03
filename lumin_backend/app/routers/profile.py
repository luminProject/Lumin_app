from __future__ import annotations

from datetime import date
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from app.core.lumin_facade import ProfileValidationError
from app.supabase_client import (
    verify_user_access,
    extract_bearer,
    get_supabase_for_jwt,
)
from app.core.lumin_facade import LuminFacade

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileOut(BaseModel):
    user_id: str
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None
    energy_source: Optional[str] = None
    has_solar_panels: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_billing_end_date: Optional[date] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None
    energy_source: Optional[str] = Field(
        default=None,
        description="Grid only or Grid + Solar",
    )
    has_solar_panels: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_billing_end_date: Optional[date] = None


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(
    user_id: str,
    authorization: Optional[str] = Header(None),
):
    try:
        verify_user_access(user_id, authorization)

        jwt = extract_bearer(authorization)
        user_supabase = get_supabase_for_jwt(jwt)
        facade = LuminFacade(user_supabase)

        return facade.get_profile(user_id)

    except HTTPException:
        raise
    except ProfileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{user_id}", response_model=ProfileOut)
def update_profile(
    user_id: str,
    payload: ProfileUpdate,
    authorization: Optional[str] = Header(None),
):
    try:
        verify_user_access(user_id, authorization)

        jwt = extract_bearer(authorization)
        user_supabase = get_supabase_for_jwt(jwt)
        facade = LuminFacade(user_supabase)

        info = payload.model_dump(exclude_none=True)


        return facade.update_profile(user_id, info)

    except HTTPException:
        raise
    except ProfileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))