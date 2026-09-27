from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["CITIZEN", "WASTE_COLLECTOR", "SUPERVISOR", "GOVERNMENT_AUTHORITY"]
Priority = Literal["LOW", "NORMAL", "HIGH", "URGENT"]
Stream = Literal["WET", "DRY", "SANITARY", "SPECIAL_CARE", "UNKNOWN_MIXED"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Register(Login):
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=12, max_length=128)


class UserCreate(Register):
    role: Role
    ward_id: int | None = None


class UserUpdate(Strict):
    active: bool
    available: bool = True


class Profile(Strict):
    name: str = Field(min_length=2, max_length=100)


class ComplaintCreate(Strict):
    description: str = Field(min_length=10, max_length=4000)
    address: str = Field(min_length=3, max_length=300)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    ward_id: int
    category_id: int
    waste_stream: Stream


class Transition(Strict):
    action: Literal[
        "review",
        "verify",
        "reject",
        "accept",
        "start",
        "submit_resolution",
        "approve",
        "return",
        "confirm",
        "reopen",
    ]
    version: int
    reason: str = Field(default="", max_length=2000)
    priority: Priority | None = None
    category_id: int | None = None


class Assign(Strict):
    collector_id: int
    version: int
    reason: str = Field(min_length=3, max_length=1000)


class FeedbackCreate(Strict):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class Named(Strict):
    name: str = Field(min_length=2, max_length=100)


class WardCreate(Named):
    zone: str = Field(min_length=2, max_length=100)


class SLACreate(Strict):
    priority: Priority
    hours: int = Field(ge=1, le=720)
