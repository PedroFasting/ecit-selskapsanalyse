"""
FastAPI-applikasjon for HR Analyse.
Tynt API-lag over eksisterende hr_database-pakke.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request

from hr import HRAnalytics, init_database

# Konfigurer stier
WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

# Delt analytics-instans (settes ved oppstart)
analytics: HRAnalytics = None  # type: ignore


def get_analytics() -> HRAnalytics:
    """Hent analytics-instans. Brukes av ruter."""
    return analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialiser database og analytics ved oppstart."""
    global analytics
    init_database()
    analytics = HRAnalytics()
    yield


app = FastAPI(
    title="HR Analyse",
    description="Analyse av ansattdata for HR-avdelingen",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — tillat alt for lokal utvikling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statiske filer og templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Importer og registrer ruter
from web.routes.analytics import router as analytics_router
from web.routes.import_routes import router as import_router
from web.routes.report import router as report_router
from web.routes.analyze import router as analyze_router
from web.routes.dashboard import router as dashboard_router

app.include_router(analytics_router, prefix="/api")
app.include_router(import_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/")
async def index(request: Request):
    """Server hovedsiden."""
    return templates.TemplateResponse(request, "index.html")


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("web.app:app", host=host, port=port, reload=True)
