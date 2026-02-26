
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ProfileBase(BaseModel):
    username: str
    email: str
    phone: Optional[str] = None
    energy_source: Optional[str] = None
    has_solar_panels: Optional[bool] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    energy_source: Optional[str] = None
    has_solar_panels: Optional[bool] = None


class ProfileOut(ProfileBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True