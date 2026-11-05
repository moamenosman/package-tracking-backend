from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.config import get_settings
from app.database import create_mongo_client


def initialize_database() -> None:
    settings = get_settings()

    print(f"Initializing database: {settings.mongodb_database}")

    with create_mongo_client(settings) as client:
        database = client[settings.mongodb_database]

        # Verify connectivity before making changes.
        database.command("ping")

        # Create only missing collections.
        existing_collections = set(database.list_collection_names())

        for collection_name in ("users", "orders"):
            if collection_name not in existing_collections:
                database.create_collection(collection_name)
                print(f"Created collection: {collection_name}")
            else:
                print(f"Collection already exists: {collection_name}")

        users = database["users"]
        orders = database["orders"]

        # Prevent duplicate stored email values.
        users.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="users_email_unique",
        )

        # Support retrieving courier accounts by role.
        users.create_index(
            [("role", ASCENDING)],
            name="users_role",
        )

        # Support owner-specific lists, newest first.
        orders.create_index(
            [
                ("owner_id", ASCENDING),
                ("created_at", DESCENDING),
                ("_id", DESCENDING),
            ],
            name="orders_owner_newest",
        )

        # Support courier-specific lists, newest first.
        orders.create_index(
            [
                ("courier_id", ASCENDING),
                ("created_at", DESCENDING),
                ("_id", DESCENDING),
            ],
            name="orders_courier_newest",
        )

        # Support the admin list, newest first.
        orders.create_index(
            [
                ("created_at", DESCENDING),
                ("_id", DESCENDING),
            ],
            name="orders_newest",
        )

        print("Indexes verified.")

        for collection_name in ("users", "orders"):
            collection = database[collection_name]
            index_names = [
                index["name"]
                for index in collection.list_indexes()
            ]

            print(f"{collection_name} indexes: {index_names}")

    print("Database initialization completed successfully.")


if __name__ == "__main__":
    try:
        initialize_database()
    except PyMongoError as error:
        # Avoid printing connection details or credentials.
        print(
            "Database initialization failed "
            f"(({type(error).__name__}): {error})."
        )
        print(
            "Check database permissions, connectivity, "
            "and existing collection/index definitions."
        )
        raise SystemExit(1) from None