from __future__ import annotations

from typing import Any, Dict, List

from app.services.device_factory import DeviceFactory
from app.services.notification_service import NotificationService
from app.services.recommendation_service import RecommendationService


class SmartEnergyFacade:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.device_factory = DeviceFactory()
        self.recommendation_service = RecommendationService(supabase_client)
        self.notification_service = NotificationService(supabase_client)

    # =========================================================
    # Recommendation Methods
    # =========================================================
    def viewRecommendations(self, user_id: str) -> Dict[str, Any]:
        """
        Generate recommendation for a user.
        If recommendation is generated successfully, also create a notification.
        """
        result = self.recommendation_service.generate_for_user(user_id)

        if result.get("success") and result.get("recommendation"):
            recommendation_data = result["recommendation"]
            recommendation_text = recommendation_data.get("recommendation_text")

            if recommendation_text:
                self.notification_service.create_recommendation_notification(
                    user_id=user_id,
                    recommendation_text=recommendation_text,
                )

        return result

    def getLatestRecommendation(self, user_id: str) -> Dict[str, Any]:
        return self.recommendation_service.get_latest_recommendation(user_id)

    def getAllRecommendations(self, user_id: str) -> Dict[str, Any]:
        return self.recommendation_service.get_all_recommendations(user_id)

    # =========================================================
    # Notification Methods
    # =========================================================
    def getNotifications(self, user_id: str) -> Dict[str, Any]:
        return self.notification_service.get_user_notifications(user_id)

    def getLatestNotification(self, user_id: str) -> Dict[str, Any]:
        return self.notification_service.get_latest_notification(user_id)

    # =========================================================
    # Device Methods
    # =========================================================
    def getUserDevices(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch all user devices from Supabase and convert them into objects
        using DeviceFactory.
        """
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .order("device_id")
            .execute()
        )

        rows = response.data or []

        if not rows:
            return {
                "success": True,
                "status": "empty",
                "code": "NO_DEVICES",
                "message": "No devices found for this user.",
                "data": [],
            }

        devices = [self.device_factory.createDevice(row) for row in rows]

        return {
            "success": True,
            "status": "success",
            "code": "DEVICES_FETCHED",
            "message": "Devices fetched successfully.",
            "data": devices,
        }

    def getUserDeviceInfos(self, user_id: str) -> Dict[str, Any]:
        """
        Returns simplified device information for UI/debugging.
        """
        devices_result = self.getUserDevices(user_id)

        if not devices_result["data"]:
            return devices_result

        info_list: List[dict] = []
        for device in devices_result["data"]:
            info_list.append(
                {
                    "device_id": device.device_id,
                    "device_name": device.device_name,
                    "device_type": device.device_type,
                    "installation_date": (
                        device.installation_date.isoformat()
                        if device.installation_date else None
                    ),
                    "user_id": device.user_id,
                    "device_info": device.getDeviceInfo(),
                }
            )

        return {
            "success": True,
            "status": "success",
            "code": "DEVICE_INFOS_FETCHED",
            "message": "Device information fetched successfully.",
            "data": info_list,
        }   