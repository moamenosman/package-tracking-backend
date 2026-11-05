from typing import Any
from app.schemas.users import UserResponse

from pymongo.database import Database

from app.schemas.orders import (
    AssignmentHistoryEntry,
    CourierInfo,
    OrderResponse,
    StatusHistoryEntry,
)


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


def optional_id_to_string(value) -> str | None:
    return str(value) if value is not None else None


def order_to_response(
    document: dict[str, Any],
    database: Database,
) -> OrderResponse:
    courier = None
    courier_id = document["courier_id"]

    if courier_id is not None:
        courier_document = database["users"].find_one(
            {"_id": courier_id},
            {"name": 1, "phone": 1},
        )

        if courier_document is not None:
            courier = CourierInfo(
                id=str(courier_document["_id"]),
                name=courier_document["name"],
                phone=courier_document["phone"],
            )

    status_history = [
        StatusHistoryEntry(
            from_status=entry["from_status"],
            to_status=entry["to_status"],
            actor_id=str(entry["actor_id"]),
            changed_at=entry["changed_at"],
        )
        for entry in document["status_history"]
    ]

    assignment_history = [
        AssignmentHistoryEntry(
            action=entry["action"],
            previous_courier_id=optional_id_to_string(
                entry["previous_courier_id"]
            ),
            courier_id=optional_id_to_string(
                entry["courier_id"]
            ),
            actor_id=str(entry["actor_id"]),
            changed_at=entry["changed_at"],
        )
        for entry in document["assignment_history"]
    ]

    return OrderResponse(
        id=str(document["_id"]),
        owner_id=str(document["owner_id"]),
        recipient=document["recipient"],
        pickup=document["pickup"],
        dropoff=document["dropoff"],
        package=document["package"],
        delivery_time=document["delivery_time"],
        delivery_instructions=document["delivery_instructions"],
        delivery_status=document["delivery_status"],
        assignment_state=document["assignment_state"],
        courier_id=optional_id_to_string(courier_id),
        courier=courier,
        status_history=status_history,
        assignment_history=assignment_history,
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )