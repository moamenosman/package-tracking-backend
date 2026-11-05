import certifi
from fastapi import Request
from pymongo import MongoClient
from pymongo.database import Database

from app.config import Settings


def create_mongo_client(settings: Settings) -> MongoClient:
    return MongoClient(
        settings.mongodb_uri.get_secret_value(),
        tlsCAFile=certifi.where(),
        connect=False,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        timeoutMS=5000,
        tz_aware=True,
    )


def get_database(request: Request) -> Database:
    return request.app.state.database