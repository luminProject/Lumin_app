from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.models.notification import Notification


class NotificationService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def create_notification(
        self,
        user_id: str,
        content: str,
        notification_type: str = "general",
    ) -> Dict[str, Any]:
        notification = Notification(
            notification_id=None,
            user_id=user_id,
            notification_type=notification_type,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )

        response = (
            self.supabase.table("notification")
            .insert(notification.to_dict())
            .execute()
        )

        data = response.data or []

        if not data:
            return {
                "success": False,
                "status": "error",
                "code": "NOTIFICATION_CREATE_FAILED",
                "message": "Notification could not be created.",
                "data": None,
            }

        return {
            "success": True,
            "status": "success",
            "code": "NOTIFICATION_CREATED",
            "message": "Notification created successfully.",
            "data": data[0],
        }

    def create_recommendation_notification(
        self,
        user_id: str,
        recommendation_text: str,
    ) -> Dict[str, Any]:
        return self.create_notification(
            user_id=user_id,
            content=recommendation_text,
            notification_type="recommendation",
        )

    def get_user_notifications(self, user_id: str) -> Dict[str, Any]:
        response = (
            self.supabase.table("notification")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .execute()
        )

        data = response.data or []

        return {
            "success": True,
            "status": "success",
            "code": "NOTIFICATIONS_FETCHED",
            "message": "Notifications fetched successfully." if data else "No notifications found for this user.",
            "data": data,
        }

    def get_latest_notification(self, user_id: str) -> Dict[str, Any]:
        response = (
            self.supabase.table("notification")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data or []

        if not data:
            return {
                "success": False,
                "status": "empty",
                "code": "NO_NOTIFICATIONS",
                "message": "No notifications found for this user.",
                "data": None,
            }

        return {
            "success": True,
            "status": "success",
            "code": "LATEST_NOTIFICATION_FETCHED",
            "message": "Latest notification fetched successfully.",
            "data": data[0],
        }