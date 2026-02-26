# lumin_backend/app/routes/profile.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.supabase_client import supabase

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileOut(BaseModel):
    user_id: UUID
    username: str | None = None
    phone_number: str | None = None
    location: str | None = None


class ProfileUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    location: str | None = None


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(user_id: UUID):
    res = (
        supabase.table("users")
        .select("user_id,username,phone_number,location")
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return res.data


@router.patch("/{user_id}", response_model=ProfileOut)
def update_profile(user_id: UUID, payload: ProfileUpdate):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided")

    res = (
        supabase.table("users")
        .update(update_data)
        .eq("user_id", str(user_id))
        .select("user_id,username,phone_number,location")
        .maybe_single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return res.data