from bson import ObjectId
from fastapi import HTTPException


def parse_object_id( value: str, field_name: str = "ID", ) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a valid MongoDB ObjectId.",
        )

    return ObjectId(value)