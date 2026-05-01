from __future__ import annotations

import logging
import os
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# ─── Initialize Firebase Admin SDK ───────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVICE_ACCOUNT_PATH = os.path.join(
    _BASE_DIR,
    "lumin-app-32044-firebase-adminsdk-fbsvc-6102df6ef4.json",
)

if not firebase_admin._apps:
    cred = credentials.Certificate(_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)


# ─── FCM Service ─────────────────────────────────────────────

class FCMService:

    @staticmethod
    def send_push(
        fcm_token: str,
        title: str,
        body: str,
    ) -> bool:
        """
        Send a push notification to a single device.
        Returns True if sent successfully, False otherwise.
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                token=fcm_token,
            )
            messaging.send(message)
            logger.info(f"✅ FCM push sent successfully.")
            return True

        except Exception as e:
            logger.error(f"❌ FCM push failed: {e}")
            return False
