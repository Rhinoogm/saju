from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.account import router as account_router
from app.api.routes.payments import router as payments_router
from app.api.routes.reading_sessions import router as reading_sessions_router
from app.api.routes.webhooks import router as webhooks_router
from app.config import get_settings
from app.services.db import close_db_pool, create_db_pool
from app.services.rate_limiter import InMemoryRateLimiter


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.llm_http_client = httpx.AsyncClient()
        app.state.llm_provider_cache = {}
        app.state.db_pool = None if settings.local_demo_enabled else await create_db_pool(settings.database_url)
        try:
            yield
        finally:
            await close_db_pool(getattr(app.state, "db_pool", None))
            client = getattr(app.state, "llm_http_client", None)
            if isinstance(client, httpx.AsyncClient) and not client.is_closed:
                await client.aclose()
            app.state.llm_provider_cache.clear()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.llm_http_client = None
    app.state.llm_provider_cache = {}
    app.state.db_pool = None

    app.state.prompt_store = None

    app.state.llm_rate_limiter = None
    if settings.rate_limit_enabled:
        app.state.llm_rate_limiter = InMemoryRateLimiter(
            per_ip_per_hour=settings.llm_rate_limit_per_ip_per_hour,
            global_per_minute=settings.llm_rate_limit_global_per_minute,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(reading_sessions_router)
    app.include_router(payments_router)
    app.include_router(account_router)
    app.include_router(webhooks_router)
    return app


app = create_app()
