from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.supabase_client import supabase
from app.core.SmartEnergyFacade import SmartEnergyFacade  # انتبهي للاسم/المسار

router = APIRouter(prefix="/profiles", tags=["profiles"])

facade = SmartEnergyFacade(supabase)


class ProfileOut(BaseModel):
    user_id: str
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(user_id: str):
    return facade.get_profile(user_id=user_id)


@router.patch("/{user_id}", response_model=ProfileOut)
def update_profile(user_id: str, payload: ProfileUpdate):
    return facade.update_profile(
        user_id=user_id,
        info=payload.model_dump(exclude_none=True),
    )