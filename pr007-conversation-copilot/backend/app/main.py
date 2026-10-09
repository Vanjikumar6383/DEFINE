import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.config import get_settings
from app.db.database import create_tables
from app.api.routes import auth, sessions, copilot, integrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating tables if needed...")
    await create_tables()
    logger.info("DB ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Conversation Copilot",
    description="A real-time, objective-aware assistant for meetings and conversations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(copilot.router)
app.include_router(integrations.router)


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}


# Serve frontend static files (when running without a separate dev server)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css_direct")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

    @app.get("/", response_class=FileResponse)
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/dashboard", response_class=FileResponse)
    async def serve_dashboard():
        return FileResponse(os.path.join(frontend_path, "dashboard.html"))

    @app.get("/integrations", response_class=FileResponse)
    async def serve_integrations():
        return FileResponse(os.path.join(frontend_path, "integrations.html"))

    @app.get("/session/{session_id}", response_class=FileResponse)
    async def serve_session(session_id: str):
        return FileResponse(os.path.join(frontend_path, "session.html"))

