from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin_prompts import router as admin_prompts_router
from app.api.routes.saju import router as saju_router
from app.config import get_settings
from app.services.prompt_store import PromptStore


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    store = PromptStore(settings.prompts_db_path)
    store.init()
    app.state.prompt_store = store

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

    app.include_router(admin_prompts_router)
    app.include_router(saju_router)
    return app


app = create_app()
