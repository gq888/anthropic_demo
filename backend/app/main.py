"""FastAPI entrypoint for the multi-agent research demo backend."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.settings import Settings, get_settings

app = FastAPI(title="Multi-Agent Research Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://8.213.146.118:5173",
        "https://8.213.146.118:5173",
        "https://gq888.github.io",
        "*",
    ],
    #allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|8\.213\.146\.118)(:\d+)?$|https://gq888\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Simple health endpoint that ensures settings load successfully."""

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }
