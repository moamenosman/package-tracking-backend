from typing import Any
from app.schemas.users import UserResponse


def user_to_response(document: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        phone=document["phone"],
        role=document["role"],
        active=document["active"],
        created_at=document["created_at"],
    )