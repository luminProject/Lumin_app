from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    username: str = ""
    password: Optional[str] = None
    phone_number: str = ""
    location: str = ""
    avatar_url: Optional[str] = None

    # --------------------------
    # OOP: تحميل البيانات داخل الكائن
    # --------------------------

    def get_profile(self, supabase) -> None:
        res = (
            supabase.table("users")
            .select("user_id, username, phone_number, location, avatar_url")
            .eq("user_id", self.user_id)
            .limit(1)
            .execute()
        )

        if getattr(res, "error", None):
            raise ValueError(str(res.error))

        rows = res.data or []
        if not rows:
            return  # يبقى الكائن بالقيم الافتراضية

        row = rows[0]

        # نخزن القيم داخل المتغيرات
        self.username = row.get("username") or ""
        self.phone_number = row.get("phone_number") or ""
        self.location = row.get("location") or ""
        self.avatar_url = row.get("avatar_url")

    # --------------------------
    # OOP: تحديث القيم داخل الكائن
    # --------------------------

    def update_profile(self, supabase, data: dict) -> None:
        if "username" in data:
            self.username = data["username"]

        if "phone_number" in data:
            self.phone_number = data["phone_number"]

        if "location" in data:
            self.location = data["location"]

        if "avatar_url" in data:
            self.avatar_url = data["avatar_url"]

        # حفظ في الداتابيس
        payload = {
            "username": self.username,
            "phone_number": self.phone_number,
            "location": self.location,
            "avatar_url": self.avatar_url,
        }

        res = (
            supabase.table("users")
            .update(payload)
            .eq("user_id", self.user_id)
            .execute()
        )

        if getattr(res, "error", None):
            raise ValueError(str(res.error))

    # --------------------------
    # تحويل للاستجابة
    # --------------------------

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "phone_number": self.phone_number,
            "location": self.location,
            "avatar_url": self.avatar_url,
        }