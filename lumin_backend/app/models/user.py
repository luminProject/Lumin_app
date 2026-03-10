from typing import Any, Dict, Optional
from pydantic import BaseModel
from supabase import Client


class User(BaseModel):
    user_id: str
    username: str = ""
    phone_number: str = ""
    location: Optional[str] = None
    avatar_url: Optional[str] = None
    energy_source: Optional[str] = "Grid only"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self) -> dict:
        return self.dict()

    @staticmethod
    def get_profile(db: Client, user_id: str) -> "User":
        resp = (
            db.table("users")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        rows = resp.data or []

        if rows:
            return User(**rows[0])

        new_row = {
            "user_id": user_id,
            "username": "",
            "phone_number": "",
            "location": None,
            "avatar_url": None,
            "energy_source": "Grid only",
            "latitude": None,
            "longitude": None,
        }

        insert_resp = db.table("users").insert(new_row).execute()
        inserted_rows = insert_resp.data or []

        if not inserted_rows:
            raise ValueError("Failed to create profile")

        return User(**inserted_rows[0])

    @staticmethod
    def update_profile(db: Client, user_id: str, info: Dict[str, Any]) -> "User":
        info.pop("user_id", None)

        User.get_profile(db, user_id)

        if not info:
            return User.get_profile(db, user_id)

        db.table("users").update(info).eq("user_id", user_id).execute()

        return User.get_profile(db, user_id)