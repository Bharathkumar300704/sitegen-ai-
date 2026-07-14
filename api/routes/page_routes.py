"""
Page routes — serves Jinja2-rendered HTML pages for the frontend.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth.dependencies import get_current_user, get_optional_user
from repositories import project_repository, generation_repository
from database.models.user import User

router = APIRouter(tags=["Pages"])


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request, user=Depends(get_optional_user)):
    """Landing page — redirect to dashboard if already logged in."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return request.app.state.templates.TemplateResponse("landing.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Login page."""
    return request.app.state.templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Registration page."""
    return request.app.state.templates.TemplateResponse("auth/register.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """User dashboard."""
    projects = project_repository.get_projects_by_user(db, user.id)
    return request.app.state.templates.TemplateResponse(
        "dashboard/index.html",
        {"request": request, "user": user, "projects": projects},
    )


@router.get("/builder", response_class=HTMLResponse)
def builder_page_new(request: Request, user: User = Depends(get_current_user)):
    """Builder page for new website (no project yet)."""
    return request.app.state.templates.TemplateResponse(
        "builder/index.html",
        {"request": request, "user": user, "project": None, "website": None},
    )


@router.get("/builder/{project_id}", response_class=HTMLResponse)
def builder_page(request: Request, project_id: str,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Builder page for an existing project."""
    project = project_repository.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    website = generation_repository.get_current_website(db, project_id)
    return request.app.state.templates.TemplateResponse(
        "builder/index.html",
        {"request": request, "user": user, "project": project, "website": website},
    )


@router.get("/preview/{project_id}", response_class=HTMLResponse)
def preview_page(request: Request, project_id: str,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Standalone preview page with responsive controls."""
    project = project_repository.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    website = generation_repository.get_current_website(db, project_id)
    return request.app.state.templates.TemplateResponse(
        "builder/preview.html",
        {"request": request, "user": user, "project": project, "website": website},
    )
