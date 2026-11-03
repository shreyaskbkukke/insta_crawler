import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .adapters import build_data_source
from .adapters.base import DataSource
from .api import router
from .collector import Collector
from .config import Settings, get_settings
from .store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, source: DataSource | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = Store(settings.data_dir)
        app.state.store.load()
        app.state.source = source or build_data_source(settings)
        app.state.collector = Collector(app.state.store, app.state.source, settings)
        await app.state.collector.resume_incomplete()
        try:
            yield
        finally:
            await app.state.collector.shutdown()
            await app.state.source.aclose()

    app = FastAPI(title="Instagram Profile Explorer", lifespan=lifespan)
    app.include_router(router)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    return app


app = create_app()
