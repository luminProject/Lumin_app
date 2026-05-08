from typing import Optional
from datetime import date


class User:
    def __init__(
        self,
        user_id: str,
        username: str = "",
        phone_number: str = "",
        location: Optional[str] = None,
        avatar_url: Optional[str] = None,
        energy_source: Optional[str] = "Grid only",
        has_solar_panels: Optional[bool] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        last_billing_end_date: Optional[date] = None,
    ):
        self._user_id = user_id
        self._username = username
        self._phone_number = phone_number
        self._location = location
        self._avatar_url = avatar_url
        self._energy_source = energy_source
        self._has_solar_panels = has_solar_panels
        self._latitude = latitude
        self._longitude = longitude
        if isinstance(last_billing_end_date, str):
            last_billing_end_date = date.fromisoformat(last_billing_end_date[:10])

        self._last_billing_end_date = last_billing_end_date

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "phone_number": self._phone_number,
            "location": self._location,
            "avatar_url": self._avatar_url,
            "energy_source": self._energy_source,
            "has_solar_panels": self._has_solar_panels,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "last_billing_end_date": self._last_billing_end_date,
        }