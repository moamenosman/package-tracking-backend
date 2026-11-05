from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.config import get_settings
from app.database import create_mongo_client, get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = create_mongo_client(settings)

    app.state.mongo_client = client
    app.state.database = client[settings.mongodb_database]

    try:
        yield
    finally:
        client.close()


app = FastAPI(
    title="PulseShip",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/health/live", tags=["Health"])
def check_liveness():
    return {"status": "200 OK"}


@app.get("/health/ready", tags=["Health"])
def check_readiness( database: Database = Depends(get_database), ):
    try:
        database.command("ping")
    except PyMongoError as err:
        print(f"Database ping failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable.",
        ) from None

    return {
        "status": "ok",
        "database": "connected",
    }