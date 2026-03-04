"""
User Domain Model

Represents a user profile inside the LUMIN system.
Responsible for retrieving and updating user data
from the Supabase database.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel
from supabase import Client


class User(BaseModel):
    """
    User entity used in the application domain.
    """

    user_id: str
    username: str = ""
    phone_number: str = ""
    location: str = ""
    avatar_url: Optional[str] = None

    energy_source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


    def to_dict(self) -> dict:
        """
        Convert User object into dictionary format
        suitable for API responses.
        """
        return self.dict()


    @staticmethod
    def get_profile(db: Client, user_id: str) -> "User":
        """
        Retrieve a user's profile from the database.
        """

        resp = (
            db.table("users")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        rows = resp.data or []

        if not rows:
            raise ValueError("Profile not found")

        return User(**rows[0])


    @staticmethod
    def update_profile(db: Client, user_id: str, info: Dict[str, Any]) -> "User":
        """
        Update user profile information.
        """

        info.pop("user_id", None)

        if not info:
            return User.get_profile(db, user_id)

        db.table("users").update(info).eq("user_id", user_id).execute()

        return User.get_profile(db, user_id)