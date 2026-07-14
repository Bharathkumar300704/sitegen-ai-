"""
SiteGen AI — Main Application Entry Point

This is the FastAPI application factory. It:
1. Creates the FastAPI app instance
2. Configures CORS, static files, and Jinja2 templates
3. Registers all API routers
4. Creates database tables on startup
5. Defines global exception handlers
"""

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from config.logging_config import setup_logging, get_logger
from database.connection import create_tables

# Initialize logging
setup_logging()
logger = get_logger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create required directories
for directory in ["static", "uploads", "generated_sites", "downloads", "logs"]:
    os.makedirs(directory, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# --- Register Routers ---
from api.routes.auth_routes import router as auth_router
from api.routes.project_routes import router as project_router
from api.routes.generation_routes import router as generation_router
from api.routes.download_routes import router as download_router
from api.routes.page_routes import router as page_router

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(generation_router)
app.include_router(download_router)
app.include_router(page_router)


# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    """Initialize database tables on application startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # Import all models so they are registered with Base
    import database.models  # noqa
    create_tables()
    logger.info("Database tables created/verified")
    logger.info(f"Server running at http://localhost:{settings.PORT}")


# --- Global Exception Handler ---
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    """Redirect to login page for unauthorized web requests."""
    if "api" not in str(request.url.path):
        return RedirectResponse(url="/login", status_code=302)
    return {"detail": "Not authenticated"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    if "api" in str(request.url.path):
        return {"detail": "Not found"}
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "user": None},
        status_code=404,
    )


# --- Run with Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
