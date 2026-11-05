from datetime import UTC, datetime

from pymongo.errors import PyMongoError

from app.config import get_settings
from app.database import create_mongo_client
from app.schemas.users import UserRegister, UserRole


DEMO_ACCOUNTS = [
    {
        "name": "Demo Seller",
        "email": "seller@example.com",
        "phone": "+15550100001",
        "password": "seller-demo",
        "role": UserRole.USER,
    },
    {
        "name": "Demo Courier One",
        "email": "courier1@example.com",
        "phone": "+15550100002",
        "password": "courier1-demo",
        "role": UserRole.COURIER,
    },
    {
        "name": "Demo Courier Two",
        "email": "courier2@example.com",
        "phone": "+15550100003",
        "password": "courier2-demo",
        "role": UserRole.COURIER,
    },
    {
        "name": "Demo Admin",
        "email": "admin@example.com",
        "phone": "+15550100004",
        "password": "admin-demo",
        "role": UserRole.ADMIN,
    },
]


def seed_demo_data() -> None:
    settings = get_settings()

    print(f"Seeding demo accounts in: {settings.mongodb_database}")

    with create_mongo_client(settings) as client:
        database = client[settings.mongodb_database]
        database.command("ping")

        users = database["users"]

        for account in DEMO_ACCOUNTS:
            # Validate the same account fields used by registration.
            # Role is supplied separately because public registration
            # must not accept it.
            validated = UserRegister(
                name=account["name"],
                email=account["email"],
                phone=account["phone"],
                password=account["password"],
            )

            document = validated.model_dump(mode="json")
            document.update(
                {
                    "role": account["role"].value,
                    "active": True,
                    "created_at": datetime.now(UTC),
                }
            )

            result = users.update_one(
                {"email": document["email"]},
                {"$setOnInsert": document},
                upsert=True,
            )

            if result.upserted_id is not None:
                print(
                    f"Created: {document['email']} "
                    f"({document['role']})"
                )
            else:
                print(
                    f"Already exists; left unchanged: "
                    f"{document['email']}"
                )

                existing = users.find_one(
                    {"email": document["email"]},
                    {"role": 1, "active": 1},
                )

                if existing and (
                    existing.get("role") != document["role"]
                    or existing.get("active") is not True
                ):
                    print(
                        "  WARNING: Existing account has a different "
                        "role or is inactive. Review it manually."
                    )

    print("Demo-account seeding completed.")


if __name__ == "__main__":
    try:
        seed_demo_data()
    except PyMongoError as error:
        print(
            f"Demo-account seeding failed "
            f"({type(error).__name__})."
        )
        print(
            "Check Atlas connectivity, permissions, "
            "and database initialization."
        )
        raise SystemExit(1) from None