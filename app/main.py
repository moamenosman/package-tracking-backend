from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.database import Database
from pymongo.errors import PyMongoError
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import create_mongo_client, get_database
from app.routers.identity import router as identity_router


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

settings = get_settings()

app = FastAPI(
    title="PulseShip",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret.get_secret_value(),
    session_cookie="pulseship_session",
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=settings.session_https_only,
)


@app.middleware("http")
async def check_browser_origin(request: Request, call_next):
    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}

    if ( request.url.path.startswith("/api/") and request.method in unsafe_methods ):
        origin = request.headers.get("origin")

        allowed_origins = {
            settings.public_origin,
            settings.api_origin,
        }

        # Browser requests with a mismatched Origin are rejected.
        # Tools such as curl may omit this header.
        if origin is not None and origin not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Request origin is not allowed."},
            )

    return await call_next(request)


@app.exception_handler(PyMongoError)
async def handle_database_error(
    request: Request,
    error: PyMongoError,
):
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable."},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request,
    error: RequestValidationError,
):
    # Do not echo request input values, which may include passwords.
    details = [
        {
            "loc": list(item["loc"]),
            "msg": item["msg"],
            "type": item["type"],
        }
        for item in error.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={"detail": details},
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


app.include_router(identity_router)