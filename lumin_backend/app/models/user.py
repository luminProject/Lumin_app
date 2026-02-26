from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    """Represents the User class exactly as shown in the class diagram."""

    user_id: int
    username: str
    password: str
    phone_number: str
    location: str

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "password": self.password,
            "phone_number": self.phone_number,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=int(data.get("user_id")),
            username=str(data.get("username")),
            password=str(data.get("password")),
            phone_number=str(data.get("phone_number")),
            location=str(data.get("location")),
        )
