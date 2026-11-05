from bson import ObjectId
from fastapi import Depends, HTTPException, Request
from pymongo.database import Database

from app.database import get_database
from app.schemas.users import UserResponse, UserRole
from app.utils.serialization import user_to_response


def get_current_user(
    request: Request,
    database: Database = Depends(get_database),
) -> UserResponse:
    user_id = request.session.get("user_id")

    if ( not isinstance(user_id, str) or not ObjectId.is_valid(user_id) ):
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="Please log in.",
        )

    document = database["users"].find_one(
        {"_id": ObjectId(user_id)},
        {"password": 0},
    )

    if ( document is None or document.get("active") is not True ):
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="Please log in.",
        )

    return user_to_response(document)


def require_admin( current_user: UserResponse = Depends(get_current_user), ) -> UserResponse:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return current_user


def require_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.role != UserRole.USER:
        raise HTTPException(
            status_code=403,
            detail="Business-owner access required.",
        )

    return current_user


def require_courier(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.role != UserRole.COURIER:
        raise HTTPException(
            status_code=403,
            detail="Courier access required.",
        )

    return current_user


def require_courier_or_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.role not in {
        UserRole.COURIER,
        UserRole.ADMIN,
    }:
        raise HTTPException(
            status_code=403,
            detail="Courier or admin access required.",
        )

    return current_user