import logging
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import get_settings
from app.db.database import create_tables
from app.api.routes import auth, sessions, copilot, integrations, tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Nimad — creating tables if needed...")
    await create_tables()
    logger.info("Nimad DB ready.")
    yield
    logger.info("Nimad shutting down.")


app = FastAPI(
    title="Nimad — AI Conversation Copilot",
    description="A real-time, objective-aware assistant for meetings and conversations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(copilot.router)
app.include_router(integrations.router)
app.include_router(tts.router)


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "app": "Nimad", "env": settings.APP_ENV}


# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css_direct")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

    # Range-capable streaming for video assets (crucial for Chrome/Edge/Safari HTML5 video autoplay)
    @app.get("/assets/{filename:path}")
    async def stream_asset(filename: str, request: Request):
        file_path = os.path.join(frontend_path, "assets", filename)
        if not os.path.exists(file_path):
            fallback_path = os.path.join(frontend_path, "assets", "background.mp4")
            if os.path.exists(fallback_path):
                file_path = fallback_path
            else:
                return Response(status_code=404)

        if filename.endswith(".mp4"):
            file_size = os.path.getsize(file_path)
            range_header = request.headers.get("Range")
            if range_header:
                m = re.match(r"bytes=(\d+)-(\d*)", range_header)
                if m:
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else file_size - 1
                    chunk_size = (end - start) + 1

                    def iterfile():
                        with open(file_path, "rb") as f:
                            f.seek(start)
                            remaining = chunk_size
                            while remaining > 0:
                                chunk = f.read(min(remaining, 64 * 1024))
                                if not chunk:
                                    break
                                remaining -= len(chunk)
                                yield chunk

                    headers = {
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(chunk_size),
                        "Content-Type": "video/mp4",
                    }
                    return StreamingResponse(iterfile(), status_code=206, headers=headers)

            return FileResponse(file_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})

        return FileResponse(file_path)

    @app.get("/", response_class=FileResponse)
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/login", response_class=FileResponse)
    async def serve_login():
        login_file = os.path.join(frontend_path, "login.html")
        if os.path.exists(login_file):
            return FileResponse(login_file)
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


