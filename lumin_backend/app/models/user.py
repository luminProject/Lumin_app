from typing import Any, Dict, Optional
from datetime import date
from pydantic import BaseModel



class User(BaseModel):
    user_id: str
    username: str = ""
    phone_number: str = ""
    location: Optional[str] = None
    avatar_url: Optional[str] = None
    energy_source: Optional[str] = "Grid only"
    has_solar_panels: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_billing_end_date: Optional[date] = None

    def to_dict(self) -> dict:
        return self.model_dump()
