from copy import deepcopy
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from app.schemas.orders import (
    OrderAssignmentInput,
    OrderCreate,
    OrderStatusInput,
)


def expect_invalid(model, payload, label):
    try:
        model.model_validate(payload)
    except ValidationError:
        print(f"PASS: {label}")
    else:
        raise AssertionError(
            f"Expected validation failure: {label}"
        )


def check_order_schemas():
    future_time = datetime.now(UTC) + timedelta(days=1)

    payload = {
        "recipient": {
            "name": "Demo Recipient",
            "phone": "+15550100010",
        },
        "pickup": {
            "address": "Demo Warehouse, Building A",
        },
        "dropoff": {
            "address": "Demo Customer Address, Building B",
        },
        "package": {
            "description": "A box containing two shirts",
            "weight_kg": 1.5,
        },
        "delivery_time": future_time.isoformat(),
        "delivery_instructions": "Call before arrival.",
    }

    order = OrderCreate.model_validate(payload)

    assert order.delivery_time.utcoffset() == timedelta(0)
    print("PASS: valid order and UTC normalization")

    missing_phone = deepcopy(payload)
    del missing_phone["recipient"]["phone"]
    expect_invalid(
        OrderCreate,
        missing_phone,
        "recipient phone is required",
    )

    empty_address = deepcopy(payload)
    empty_address["pickup"]["address"] = "   "
    expect_invalid(
        OrderCreate,
        empty_address,
        "whitespace-only address rejected",
    )

    invalid_weight = deepcopy(payload)
    invalid_weight["package"]["weight_kg"] = -1
    expect_invalid(
        OrderCreate,
        invalid_weight,
        "negative weight rejected",
    )

    past_delivery = deepcopy(payload)
    past_delivery["delivery_time"] = (
        datetime.now(UTC) - timedelta(days=1)
    ).isoformat()
    expect_invalid(
        OrderCreate,
        past_delivery,
        "past delivery time rejected",
    )

    missing_timezone = deepcopy(payload)
    missing_timezone["delivery_time"] = (
        future_time.replace(tzinfo=None).isoformat()
    )
    expect_invalid(
        OrderCreate,
        missing_timezone,
        "delivery time requires timezone",
    )

    supplied_owner = deepcopy(payload)
    supplied_owner["owner_id"] = "client-chosen-owner"
    expect_invalid(
        OrderCreate,
        supplied_owner,
        "client cannot supply owner_id",
    )

    expect_invalid(
        OrderAssignmentInput,
        {"courier_id": "not-a-valid-id"},
        "invalid courier ID rejected",
    )

    expect_invalid(
        OrderStatusInput,
        {"delivery_status": "TELEPORTED"},
        "unknown delivery status rejected",
    )

    print("All order-schema checks passed.")


if __name__ == "__main__":
    check_order_schemas()