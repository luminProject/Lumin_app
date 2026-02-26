from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.supabase_client import supabase

from app.models.profile import ProfileOut, ProfileUpdate

# NOTE: We keep routes here to avoid import errors until we split into separate route files.
router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(user_id: UUID):
    res = (
        supabase
        .table("users")
        .select("user_id,username,phone_number,location")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return res.data[0]


@router.patch("/{user_id}", response_model=ProfileOut)
def update_profile(user_id: UUID, payload: ProfileUpdate):
    update_data = {
        key: value
        for key, value in payload.model_dump().items()
        if value is not None
    }

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided")

    res = (
        supabase
        .table("users")
        .update(update_data)
        .eq("user_id", str(user_id))
        .select("user_id,username,phone_number,location")
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return res.data[0]
