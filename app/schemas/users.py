from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

class UserRole(str, Enum):
    USER = "user"
    COURIER = "courier"
    ADMIN = "admin"


class AccountInput(BaseModel):
    """Shared email validation for registration and login."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserRegister(AccountInput):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=30)
    password: str = Field(
        min_length=1,
        max_length=128,
        repr=False,
    )

    @field_validator("name", "phone", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class UserLogin(AccountInput):
    password: str = Field(
        min_length=1,
        max_length=128,
        repr=False,
    )


class UserResponse(BaseModel):
    """Public account information. Never includes a password."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    email: EmailStr
    phone: str
    role: UserRole
    active: bool
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


class CourierListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int