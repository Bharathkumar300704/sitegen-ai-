"""
Project API routes — CRUD operations for projects.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.project_schema import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from services.project_service import ProjectService
from auth.dependencies import get_current_user
from database.models.user import User

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all projects for the current user."""
    projects = ProjectService.get_user_projects(db, user.id)
    return {"projects": projects, "total": len(projects)}


@router.post("", response_model=ProjectResponse)
def create_project(data: ProjectCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Create a new project."""
    project = ProjectService.create_project(
        db, user.id, name=data.name,
        description=data.description, website_type=data.website_type,
    )
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Get a single project by ID."""
    try:
        return ProjectService.get_project(db, project_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, data: ProjectUpdate,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a project."""
    try:
        return ProjectService.update_project(
            db, project_id, user.id,
            name=data.name, description=data.description, website_type=data.website_type,
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Delete a project and all its generated websites."""
    try:
        ProjectService.delete_project(db, project_id, user.id)
        return {"message": "Project deleted"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
