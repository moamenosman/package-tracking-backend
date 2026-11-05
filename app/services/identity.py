from datetime import UTC, datetime

from fastapi import HTTPException
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.schemas.users import (
    CourierListResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserRole,
)
from app.utils.serialization import user_to_response


def register_user(
    database: Database,
    data: UserRegister,
) -> UserResponse:
    document = data.model_dump(mode="json")
    document.update(
        {
            "role": UserRole.USER.value,
            "active": True,
            "created_at": datetime.now(UTC),
        }
    )

    try:
        result = database["users"].insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        ) from None

    document["_id"] = result.inserted_id

    return user_to_response(document)


def authenticate_user(
    database: Database,
    data: UserLogin,
) -> UserResponse:
    document = database["users"].find_one(
        {"email": str(data.email)}
    )

    # Classroom shortcut: fictional plaintext passwords only.
    if ( document is None
        or document.get("active") is not True
        or document.get("password") != data.password ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    return user_to_response(document)


def list_couriers(
    database: Database,
    page: int,
    page_size: int,
) -> CourierListResponse:
    query = {
        "role": UserRole.COURIER.value,
        "active": True,
    }

    users = database["users"]
    total = users.count_documents(query)

    documents = (
        users.find(query, {"password": 0})
        .sort([("name", 1), ("_id", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return CourierListResponse(
        items=[
            user_to_response(document)
            for document in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
    )