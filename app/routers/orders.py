from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.database import get_database
from app.dependencies import (
    get_current_user,
    require_admin,
    require_courier,
    require_courier_or_admin,
    require_user,
)
from app.schemas.orders import (
    OrderAssignmentInput,
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatusInput,
)
from app.schemas.users import MessageResponse, UserResponse
from app.services import orders as order_service


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


@router.post("",response_model=OrderResponse,status_code=201,)
def create_order(
    data: OrderCreate,
    database: Database = Depends(get_database),
    owner: UserResponse = Depends(require_user),
):
    return order_service.create_order(database, data, owner)


@router.get(
    "",
    response_model=OrderListResponse,
)
def get_all_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    database: Database = Depends(get_database),
    admin: UserResponse = Depends(require_admin),
):
    return order_service.list_all_orders(
        database,
        page,
        page_size,
    )


# Fixed paths must precede /{order_id}.
@router.get(
    "/mine",
    response_model=OrderListResponse,
)
def get_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    database: Database = Depends(get_database),
    owner: UserResponse = Depends(require_user),
):
    return order_service.list_my_orders(
        database,
        owner,
        page,
        page_size,
    )


@router.get(
    "/assigned",
    response_model=OrderListResponse,
)
def get_assigned_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    database: Database = Depends(get_database),
    courier: UserResponse = Depends(require_courier),
):
    return order_service.list_assigned_orders(
        database,
        courier,
        page,
        page_size,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order_details(
    order_id: str,
    database: Database = Depends(get_database),
    actor: UserResponse = Depends(get_current_user),
):
    return order_service.get_order_details(
        database,
        order_id,
        actor,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    order_id: str,
    database: Database = Depends(get_database),
    owner: UserResponse = Depends(require_user),
):
    return order_service.cancel_order(
        database,
        order_id,
        owner,
    )


@router.patch(
    "/{order_id}/assignment",
    response_model=OrderResponse,
)
def assign_order(
    order_id: str,
    data: OrderAssignmentInput,
    database: Database = Depends(get_database),
    admin: UserResponse = Depends(require_admin),
):
    return order_service.assign_order(
        database,
        order_id,
        data,
        admin,
    )


@router.post(
    "/{order_id}/accept",
    response_model=OrderResponse,
)
def accept_assignment(
    order_id: str,
    database: Database = Depends(get_database),
    courier: UserResponse = Depends(require_courier),
):
    return order_service.respond_to_assignment(
        database,
        order_id,
        courier,
        accept=True,
    )


@router.post(
    "/{order_id}/decline",
    response_model=OrderResponse,
)
def decline_assignment(
    order_id: str,
    database: Database = Depends(get_database),
    courier: UserResponse = Depends(require_courier),
):
    return order_service.respond_to_assignment(
        database,
        order_id,
        courier,
        accept=False,
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
def update_status(
    order_id: str,
    data: OrderStatusInput,
    database: Database = Depends(get_database),
    actor: UserResponse = Depends(require_courier_or_admin),
):
    return order_service.update_delivery_status(
        database,
        order_id,
        data,
        actor,
    )


@router.delete(
    "/{order_id}",
    response_model=MessageResponse,
)
def delete_order(
    order_id: str,
    database: Database = Depends(get_database),
    admin: UserResponse = Depends(require_admin),
):
    order_service.delete_order(
        database,
        order_id,
        admin,
    )

    return MessageResponse(message="Order deleted successfully.")