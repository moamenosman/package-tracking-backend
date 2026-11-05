from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from bson import ObjectId
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class InputModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class AddressInput(InputModel):
    address: str = Field(min_length=1, max_length=500)


class RecipientInput(InputModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=30)


class PackageInput(InputModel):
    description: str = Field(min_length=1, max_length=1000)
    weight_kg: float | None = Field(
        default=None,
        gt=0,
        allow_inf_nan=False,
    )


class OrderCreate(InputModel):
    recipient: RecipientInput
    pickup: AddressInput
    dropoff: AddressInput
    package: PackageInput

    delivery_time: AwareDatetime
    delivery_instructions: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("delivery_time")
    @classmethod
    def validate_delivery_time(cls, value: datetime) -> datetime:
        value = value.astimezone(UTC)

        if value <= datetime.now(UTC):
            raise ValueError(
                "Delivery time must be in the future."
            )

        return value


class OrderAssignmentInput(InputModel):
    courier_id: str

    @field_validator("courier_id")
    @classmethod
    def validate_courier_id(cls, value: str) -> str:
        if not ObjectId.is_valid(value):
            raise ValueError(
                "Courier ID must be a valid MongoDB ObjectId."
            )

        return str(ObjectId(value))


class OrderStatusInput(InputModel):
    delivery_status: DeliveryStatus



class AssignmentState(str, Enum):
    UNASSIGNED = "UNASSIGNED"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"


class CourierInfo(BaseModel):
    id: str
    name: str
    phone: str


class StatusHistoryEntry(BaseModel):
    from_status: DeliveryStatus | None
    to_status: DeliveryStatus
    actor_id: str
    changed_at: datetime


class AssignmentHistoryEntry(BaseModel):
    action: Literal[
        "offered",
        "accepted",
        "declined",
        "reassigned",
        "cleared",
    ]
    previous_courier_id: str | None
    courier_id: str | None
    actor_id: str
    changed_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    owner_id: str

    recipient: RecipientInput
    pickup: AddressInput
    dropoff: AddressInput
    package: PackageInput

    delivery_time: datetime
    delivery_instructions: str | None

    delivery_status: DeliveryStatus
    assignment_state: AssignmentState

    courier_id: str | None
    courier: CourierInfo | None

    status_history: list[StatusHistoryEntry]
    assignment_history: list[AssignmentHistoryEntry]

    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int