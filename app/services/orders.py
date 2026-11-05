from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.database import Database

from app.schemas.orders import (
    AssignmentState,
    DeliveryStatus,
    OrderAssignmentInput,
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatusInput,
)
from app.schemas.users import UserResponse, UserRole
from app.utils.ids import parse_object_id
from app.utils.serialization import order_to_response


def create_order(
    database: Database,
    data: OrderCreate,
    owner: UserResponse,
) -> OrderResponse:
    now = datetime.now(UTC)
    owner_id = ObjectId(owner.id)

    document = data.model_dump()
    document.update(
        {
            "owner_id": owner_id,
            "delivery_status": DeliveryStatus.PENDING.value,
            "assignment_state": AssignmentState.UNASSIGNED.value,
            "courier_id": None,
            "status_history": [
                {
                    "from_status": None,
                    "to_status": DeliveryStatus.PENDING.value,
                    "actor_id": owner_id,
                    "changed_at": now,
                }
            ],
            "assignment_history": [],
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
            "revision": 0,
        }
    )

    result = database["orders"].insert_one(document)
    document["_id"] = result.inserted_id

    return order_to_response(document, database)


def list_my_orders(
    database: Database,
    owner: UserResponse,
    page: int,
    page_size: int,
) -> OrderListResponse:
    query = {
        "owner_id": ObjectId(owner.id),
        "deleted_at": None,
    }

    orders = database["orders"]
    total = orders.count_documents(query)

    documents = (
        orders.find(query)
        .sort([("created_at", -1), ("_id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return OrderListResponse(
        items=[order_to_response(document, database) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_accessible_order(
    database: Database,
    order_id: str,
    actor: UserResponse,
) -> dict:
    parsed_id = parse_object_id(order_id, "Order ID")
    actor_id = ObjectId(actor.id)

    query = {
        "_id": parsed_id,
        "deleted_at": None,
    }

    if actor.role == UserRole.USER:
        query["owner_id"] = actor_id
    elif actor.role == UserRole.COURIER:
        query["courier_id"] = actor_id
    elif actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Access is not allowed.",
        )

    document = database["orders"].find_one(query)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return document


def get_order_details(
    database: Database,
    order_id: str,
    actor: UserResponse,
) -> OrderResponse:
    document = get_accessible_order(
        database,
        order_id,
        actor,
    )

    return order_to_response(document, database)


def cancel_order(
    database: Database,
    order_id: str,
    owner: UserResponse,
) -> OrderResponse:
    document = get_accessible_order(
        database,
        order_id,
        owner,
    )

    cancellable_statuses = {
        DeliveryStatus.PENDING.value,
        DeliveryStatus.PICKED_UP.value,
        DeliveryStatus.IN_TRANSIT.value,
    }

    if document["delivery_status"] not in cancellable_statuses:
        raise HTTPException(
            status_code=409,
            detail="Delivered or cancelled orders cannot be cancelled.",
        )

    now = datetime.now(UTC)
    actor_id = ObjectId(owner.id)

    history_updates = {
        "status_history": {
            "from_status": document["delivery_status"],
            "to_status": DeliveryStatus.CANCELLED.value,
            "actor_id": actor_id,
            "changed_at": now,
        }
    }

    if document["courier_id"] is not None:
        history_updates["assignment_history"] = {
            "action": "cleared",
            "previous_courier_id": document["courier_id"],
            "courier_id": None,
            "actor_id": actor_id,
            "changed_at": now,
        }

    updated_document = database["orders"].find_one_and_update(
        {
            "_id": document["_id"],
            "owner_id": actor_id,
            "deleted_at": None,
            "revision": document["revision"],
            "delivery_status": document["delivery_status"],
        },
        {
            "$set": {
                "delivery_status": DeliveryStatus.CANCELLED.value,
                "assignment_state": AssignmentState.UNASSIGNED.value,
                "courier_id": None,
                "updated_at": now,
            },
            "$push": history_updates,
            "$inc": {"revision": 1},
        },
        return_document=ReturnDocument.AFTER,
    )

    if updated_document is None:
        raise HTTPException(
            status_code=409,
            detail="Order changed. Refresh it and try again.",
        )

    return order_to_response(updated_document, database)


def list_orders(
    database: Database,
    query: dict,
    page: int,
    page_size: int,
) -> OrderListResponse:
    orders = database["orders"]

    total = orders.count_documents(query)

    documents = (
        orders.find(query)
        .sort([("created_at", -1), ("_id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return OrderListResponse(
        items=[
            order_to_response(document, database)
            for document in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def update_order_with_revision(
    database: Database,
    document: dict,
    changes: dict,
    history_updates: dict | None = None,
    extra_filter: dict | None = None,
) -> dict:
    query = {
        "_id": document["_id"],
        "deleted_at": None,
        "revision": document["revision"],
        "delivery_status": document["delivery_status"],
    }

    if extra_filter:
        query.update(extra_filter)

    update = {
        "$set": changes,
        "$inc": {"revision": 1},
    }

    if history_updates:
        update["$push"] = history_updates

    updated_document = database["orders"].find_one_and_update(
        query,
        update,
        return_document=ReturnDocument.AFTER,
    )

    if updated_document is None:
        raise HTTPException(
            status_code=409,
            detail="Order changed. Refresh it and try again.",
        )

    return updated_document



def list_all_orders(
    database: Database,
    page: int,
    page_size: int,
) -> OrderListResponse:
    return list_orders(
        database,
        {"deleted_at": None},
        page,
        page_size,
    )


def list_assigned_orders(
    database: Database,
    courier: UserResponse,
    page: int,
    page_size: int,
) -> OrderListResponse:
    return list_orders(
        database,
        {
            "courier_id": ObjectId(courier.id),
            "deleted_at": None,
        },
        page,
        page_size,
    )


def assign_order(
    database: Database,
    order_id: str,
    data: OrderAssignmentInput,
    admin: UserResponse,
) -> OrderResponse:
    document = get_accessible_order(
        database,
        order_id,
        admin,
    )

    if document["delivery_status"] != DeliveryStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail="Only pending orders can be assigned or reassigned.",
        )

    courier_id = parse_object_id(data.courier_id, "Courier ID")

    courier = database["users"].find_one(
        {
            "_id": courier_id,
            "role": UserRole.COURIER.value,
            "active": True,
        },
        {"_id": 1},
    )

    if courier is None:
        raise HTTPException(
            status_code=404,
            detail="Active courier not found.",
        )

    previous_courier_id = document["courier_id"]

    if previous_courier_id == courier_id:
        raise HTTPException(
            status_code=409,
            detail="This courier is already assigned.",
        )

    now = datetime.now(UTC)

    action = (
        "reassigned"
        if previous_courier_id is not None
        else "offered"
    )

    updated_document = update_order_with_revision(
        database,
        document,
        changes={
            "courier_id": courier_id,
            "assignment_state": AssignmentState.OFFERED.value,
            "updated_at": now,
        },
        history_updates={
            "assignment_history": {
                "action": action,
                "previous_courier_id": previous_courier_id,
                "courier_id": courier_id,
                "actor_id": ObjectId(admin.id),
                "changed_at": now,
            }
        },
    )

    return order_to_response(updated_document, database)


def respond_to_assignment(
    database: Database,
    order_id: str,
    courier: UserResponse,
    accept: bool,
) -> OrderResponse:
    document = get_accessible_order(
        database,
        order_id,
        courier,
    )

    if document["delivery_status"] != DeliveryStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail="Assignments can be accepted or declined only before pickup.",
        )

    if accept:
        if document["assignment_state"] != AssignmentState.OFFERED.value:
            raise HTTPException(
                status_code=409,
                detail="Only an offered assignment can be accepted.",
            )
    elif document["assignment_state"] not in {
        AssignmentState.OFFERED.value,
        AssignmentState.ACCEPTED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail="There is no active assignment to decline.",
        )

    now = datetime.now(UTC)
    courier_id = ObjectId(courier.id)

    updated_document = update_order_with_revision(
        database,
        document,
        changes={
            "courier_id": courier_id if accept else None,
            "assignment_state": (
                AssignmentState.ACCEPTED.value
                if accept
                else AssignmentState.UNASSIGNED.value
            ),
            "updated_at": now,
        },
        history_updates={
            "assignment_history": {
                "action": "accepted" if accept else "declined",
                "previous_courier_id": courier_id,
                "courier_id": courier_id if accept else None,
                "actor_id": courier_id,
                "changed_at": now,
            }
        },
        extra_filter={"courier_id": courier_id},
    )

    return order_to_response(updated_document, database)


def update_delivery_status(
    database: Database,
    order_id: str,
    data: OrderStatusInput,
    actor: UserResponse,
) -> OrderResponse:
    document = get_accessible_order(
        database,
        order_id,
        actor,
    )

    allowed_next_status = {
        DeliveryStatus.PENDING.value: DeliveryStatus.PICKED_UP.value,
        DeliveryStatus.PICKED_UP.value: DeliveryStatus.IN_TRANSIT.value,
        DeliveryStatus.IN_TRANSIT.value: DeliveryStatus.DELIVERED.value,
    }

    current_status = document["delivery_status"]
    requested_status = data.delivery_status.value

    if allowed_next_status.get(current_status) != requested_status:
        raise HTTPException(
            status_code=409,
            detail="Invalid delivery-status transition.",
        )

    if (
        document["courier_id"] is None
        or document["assignment_state"] not in {
            AssignmentState.OFFERED.value,
            AssignmentState.ACCEPTED.value,
        }
    ):
        raise HTTPException(
            status_code=409,
            detail="An active courier assignment is required.",
        )

    now = datetime.now(UTC)
    actor_id = ObjectId(actor.id)

    changes = {
        "delivery_status": requested_status,
        "updated_at": now,
    }

    history_updates = {
        "status_history": {
            "from_status": current_status,
            "to_status": requested_status,
            "actor_id": actor_id,
            "changed_at": now,
        }
    }

    # Starting pickup implicitly acknowledges an offered assignment.
    if (
        requested_status == DeliveryStatus.PICKED_UP.value
        and document["assignment_state"] == AssignmentState.OFFERED.value
    ):
        changes["assignment_state"] = AssignmentState.ACCEPTED.value

        history_updates["assignment_history"] = {
            "action": "accepted",
            "previous_courier_id": document["courier_id"],
            "courier_id": document["courier_id"],
            "actor_id": actor_id,
            "changed_at": now,
        }

    extra_filter = {}

    if actor.role == UserRole.COURIER:
        extra_filter["courier_id"] = actor_id

    updated_document = update_order_with_revision(
        database,
        document,
        changes=changes,
        history_updates=history_updates,
        extra_filter=extra_filter,
    )

    return order_to_response(updated_document, database)


def delete_order(
    database: Database,
    order_id: str,
    admin: UserResponse,
) -> None:
    document = get_accessible_order(
        database,
        order_id,
        admin,
    )

    now = datetime.now(UTC)

    changes = {
        "deleted_at": now,
        "deleted_by": ObjectId(admin.id),
        "updated_at": now,
        "courier_id": None,
        "assignment_state": AssignmentState.UNASSIGNED.value,
    }

    history_updates = None

    if document["courier_id"] is not None:
        history_updates = {
            "assignment_history": {
                "action": "cleared",
                "previous_courier_id": document["courier_id"],
                "courier_id": None,
                "actor_id": ObjectId(admin.id),
                "changed_at": now,
            }
        }

    update_order_with_revision(
        database,
        document,
        changes=changes,
        history_updates=history_updates,
    )