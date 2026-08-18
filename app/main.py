"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.exceptions import register_exception_handlers
from app.api.routes.analytics import router as analytics_router
from app.api.routes.escalations import router as escalations_router
from app.api.routes.health import router as health_router
from app.api.routes.portal import router as portal_router
from app.api.routes.runs import router as runs_router
from app.api.routes.tickets import router as tickets_router
from app.config import get_settings
from app.graph.workflow import build_support_graph, create_checkpointer
from app.observability.logging import setup_logging
from app.observability.tracing import setup_tracing
from app.persistence import close_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    setup_logging()
    setup_tracing()

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis

    checkpointer, pool = await create_checkpointer()
    app.state.checkpointer_pool = pool
    app.state.support_graph = await build_support_graph(checkpointer=checkpointer)

    logger.info("Application started: %s", settings.app_name)
    yield

    await redis.aclose()
    await pool.close()
    await close_db()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    origins = settings.parsed_cors_origins()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(portal_router)
    app.include_router(tickets_router)
    app.include_router(escalations_router)
    app.include_router(runs_router)
    app.include_router(analytics_router)

    return app


app = create_app()
