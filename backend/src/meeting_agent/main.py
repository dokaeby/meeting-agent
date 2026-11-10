from collections import defaultdict, deque
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import Settings
from .db import make_database
from .models import Base, Organization
from .modules import deliveries, identity, integrations, meetings, minutes, organizations


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    engine, factory = make_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        if settings.environment == "test":
            Base.metadata.create_all(engine)
            with factory.begin() as db:
                if not db.get(Organization, "system"):
                    db.add(Organization(id="system", name="system"))
        yield
        engine.dispose()

    app = FastAPI(title="Meeting Agent", version="0.1.0", lifespan=lifespan)
    app.state.settings, app.state.engine, app.state.factory = settings, engine, factory
    limits = defaultdict(deque)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        request_id = str(uuid4())
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
            if origin != settings.public_url.rstrip("/"):
                return JSONResponse(
                    {
                        "code": "origin_denied",
                        "message": "허용되지 않은 Origin",
                        "request_id": request_id,
                    },
                    status_code=403,
                )
        # Per-process local abuse control; gateway applies shared production rate limits.
        if "/auth/" in request.url.path and request.method == "POST":
            from .models import now

            key = (request.client.host, request.url.path)
            window = limits[key]
            while window and window[0] < now() - 60:
                window.popleft()
            if len(window) >= 20:
                return JSONResponse(
                    {
                        "code": "rate_limit",
                        "message": "잠시 후 다시 시도해 주세요",
                        "request_id": request_id,
                    },
                    status_code=429,
                )
            window.append(now())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "request_id": request.headers.get("X-Request-ID", ""),
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(
            {
                "code": "validation",
                "message": "입력값을 확인해 주세요",
                "fields": [
                    {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                    for e in exc.errors()
                ],
            },
            status_code=422,
        )

    app.include_router(identity.router, prefix="/api/v1")
    app.include_router(organizations.router, prefix="/api/v1")
    app.include_router(meetings.router, prefix="/api/v1")
    app.include_router(minutes.router, prefix="/api/v1")
    app.include_router(deliveries.router, prefix="/api/v1")
    app.include_router(integrations.router, prefix="/api/v1")

    @app.get("/api/v1/health/live")
    def live():
        return {"status": "ok", "provider_mode": settings.provider_mode}

    @app.get("/api/v1/health/ready")
    def ready():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app
