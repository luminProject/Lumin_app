from app.models.user import User


class SmartEnergyFacade:
    """
    Facade layer:
    Routes (and the frontend indirectly) should call this single entry point
    instead of orchestrating multiple models/services directly.
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    # -----------------------------
    # Sensor reading ingestion
    # -----------------------------
    def ingest_sensor_reading(
        self,
        *,
        device_id: int,
        kwh_value: float,
        reading_time_iso: str,
    ) -> dict:
        # Verify device exists
        device_res = (
            self.supabase.table("device")
            .select("user_id")
            .eq("device_id", device_id)
            .limit(1)
            .execute()
        )

        if not device_res.data:
            raise ValueError("Device not found")

        row = {
            "device_id": device_id,
            "reading_time": reading_time_iso,
            "kwh_value": float(kwh_value),
        }

        result = self.supabase.table("sensor_data").insert(row).execute()
        return {"status": "stored", "data": result.data}

    # -----------------------------
    # Energy aggregation
    # -----------------------------
    def get_energy(self, *, user_id: str) -> dict:
        # Fetch user's devices
        devices_res = (
            self.supabase.table("device")
            .select("device_id")
            .eq("user_id", user_id)
            .execute()
        )

        if not devices_res.data:
            raise ValueError("No devices found")

        device_ids = [
            d["device_id"]
            for d in devices_res.data
            if d.get("device_id") is not None
        ]

        if not device_ids:
            raise ValueError("No valid device_id found")

        # Fetch sensor readings for these devices
        result = (
            self.supabase.table("sensor_data")
            .select("kwh_value, reading_time, device_id")
            .in_("device_id", device_ids)
            .order("reading_time", desc=True)
            .execute()
        )

        if not result.data:
            raise ValueError("No energy data found")

        total_today = sum(float(i.get("kwh_value") or 0) for i in result.data)

        return {
            "user_id": user_id,
            "total_kwh_today": total_today,
            "latest": result.data[0],
        }
    
   # for pofile page shrooq
    # --------------------------
    # Profile
    # --------------------------

    def get_profile(self, *, user_id: str) -> dict:
        user = User(user_id=user_id)
        user.get_profile(self.supabase)
        return user.to_dict()

    def update_profile(self, *, user_id: str, info: dict) -> dict:
        user = User(user_id=user_id)
        user.get_profile(self.supabase)  # تحميل أولاً
        user.update_profile(self.supabase, info)
        return user.to_dict()
        user = User.load(self.supabase, user_id)

        # عدلي فقط اللي جايك
        if "username" in info:
            user.username = info["username"] or ""

        if "phone_number" in info:
            user.phone_number = info["phone_number"] or ""

        if "location" in info:
            user.location = info["location"] or ""

        if "avatar_url" in info:
            user.avatar_url = info["avatar_url"]

        user.save(self.supabase)
        return user.to_response()
        user = User.load(self.supabase, user_id)

        # نعدل القيم داخل الكائن
        if "username" in info:
            user.username = info["username"]

        if "phone_number" in info:
            user.phone_number = info["phone_number"]

        if "location" in info:
            user.location = info["location"]

        if "avatar_url" in info:
            user.avatar_url = info["avatar_url"]

        # نحفظ
        user.save(self.supabase)

        return user.to_response()
        allowed = {"username", "phone_number", "location", "avatar_url"}
        payload = {k: v for k, v in info.items() if k in allowed and v is not None}

        # ما فيه شي يتحدث
        if not payload:
            return self.get_profile(user_id=user_id)

        res = (
            self.supabase.table("users")
            .update(payload)
            .eq("user_id", user_id)
            .execute()
        )

        if getattr(res, "error", None):
            raise ValueError(str(res.error))

        return self.get_profile(user_id=user_id)
        res = (
            self.supabase.table("users")
            .select("user_id,username,phone_number,location")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        data = getattr(res, "data", None)
        if data:
            return data

        return {"user_id": user_id, "username": "", "phone_number": "", "location": ""}