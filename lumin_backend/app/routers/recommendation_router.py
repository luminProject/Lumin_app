from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.lumin_facade import LuminFacade
from app.supabase_client import get_supabase_for_jwt


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)

security = HTTPBearer()


def get_facade(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> LuminFacade:
    jwt = credentials.credentials
    supabase = get_supabase_for_jwt(jwt)
    return LuminFacade(supabase)


@router.post("/generate/{user_id}")
def generate_recommendation(
    user_id: str,
    facade: LuminFacade = Depends(get_facade),
):
    try:
        return facade.viewRecommendations(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendation: {str(e)}",
        )


@router.get("/latest/{user_id}")
def get_latest_recommendation(
    user_id: str,
    facade: LuminFacade = Depends(get_facade),
):
    try:
        return facade.getLatestRecommendation(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latest recommendation: {str(e)}",
        )


@router.get("/all/{user_id}")
def get_all_recommendations(
    user_id: str,
    facade: LuminFacade = Depends(get_facade),
):
    try:
        return facade.getAllRecommendations(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recommendations: {str(e)}",
        )


@router.get("/notifications/{user_id}")
def get_user_notifications(
    user_id: str,
    facade: LuminFacade = Depends(get_facade),
):
    try:
        return facade.getNotifications(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch notifications: {str(e)}",
        )


@router.get("/notifications/latest/{user_id}")
def get_latest_notification(
    user_id: str,
    facade: LuminFacade = Depends(get_facade),
):
    try:
        return facade.getLatestNotification(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latest notification: {str(e)}",
        )


@router.get("/devices/{user_id}")
def get_user_devices(
    user_id: str,
    facade: LuminFacade = Depends(get_facade),
):
    try:
        return facade.getUserDeviceInfos(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch devices: {str(e)}",
        )