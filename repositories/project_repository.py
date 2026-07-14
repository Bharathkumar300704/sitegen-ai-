"""
Project repository — database operations for projects.
"""

from sqlalchemy.orm import Session
from database.models.project import Project
from typing import List


def create_project(db: Session, user_id: str, name: str, description: str = None, website_type: str = None) -> Project:
    """Create a new project."""
    project = Project(
        user_id=user_id,
        name=name,
        description=description,
        website_type=website_type,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects_by_user(db: Session, user_id: str) -> List[Project]:
    """Get all projects for a user, ordered by newest first."""
    return db.query(Project).filter(Project.user_id == user_id).order_by(Project.created_at.desc()).all()


def get_project_by_id(db: Session, project_id: str) -> Project | None:
    """Get a single project by ID."""
    return db.query(Project).filter(Project.id == project_id).first()


def update_project(db: Session, project: Project, **kwargs) -> Project:
    """Update project fields."""
    for key, value in kwargs.items():
        if hasattr(project, key) and value is not None:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project):
    """Delete a project (cascades to websites and requests)."""
    db.delete(project)
    db.commit()
