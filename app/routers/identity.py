from fastapi import APIRouter, Depends, Query, Request
from pymongo.database import Database

from app.database import get_database
from app.dependencies import get_current_user, require_admin
from app.schemas.users import (
    CourierListResponse,
    MessageResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services import identity as identity_service


router = APIRouter(prefix="/api", tags=["Identity"])


@router.post( "/auth/register", response_model=UserResponse, status_code=201, )
def register( data: UserRegister, database: Database = Depends(get_database), ):
    return identity_service.register_user(database, data)


@router.post( "/auth/login",response_model=UserResponse, )
def login( data: UserLogin, request: Request, database: Database = Depends(get_database), ):
    # A login attempt replaces the current login context.
    request.session.clear()

    user = identity_service.authenticate_user(database, data)
    request.session["user_id"] = user.id

    return user


@router.post( "/auth/logout", response_model=MessageResponse, )
def logout(request: Request):
    request.session.clear()

    return MessageResponse(message="Logged out successfully.")


@router.get( "/auth/me", response_model=UserResponse, )
def get_me( current_user: UserResponse = Depends(get_current_user), ):
    return current_user


@router.get( "/couriers", response_model=CourierListResponse, )
def get_couriers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    database: Database = Depends(get_database),
    admin: UserResponse = Depends(require_admin),
):
    return identity_service.list_couriers(
        database,
        page,
        page_size,
    )