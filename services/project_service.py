"""
Project service — business logic for project management.
"""

from sqlalchemy.orm import Session
from repositories import project_repository
from config.logging_config import get_logger

logger = get_logger(__name__)


class ProjectService:

    @staticmethod
    def create_project(db: Session, user_id: str, name: str,
                       description: str = None, website_type: str = None):
        """Create a new project for the user."""
        project = project_repository.create_project(db, user_id, name, description, website_type)
        logger.info(f"Project created: {project.id} by user {user_id}")
        return project

    @staticmethod
    def get_user_projects(db: Session, user_id: str):
        """Get all projects belonging to a user."""
        return project_repository.get_projects_by_user(db, user_id)

    @staticmethod
    def get_project(db: Session, project_id: str, user_id: str):
        """Get a project, verifying ownership."""
        project = project_repository.get_project_by_id(db, project_id)
        if not project:
            raise ValueError("Project not found")
        if project.user_id != user_id:
            raise PermissionError("Access denied")
        return project

    @staticmethod
    def update_project(db: Session, project_id: str, user_id: str, **kwargs):
        """Update a project, verifying ownership."""
        project = ProjectService.get_project(db, project_id, user_id)
        return project_repository.update_project(db, project, **kwargs)

    @staticmethod
    def delete_project(db: Session, project_id: str, user_id: str):
        """Delete a project, verifying ownership."""
        project = ProjectService.get_project(db, project_id, user_id)
        project_repository.delete_project(db, project)
        logger.info(f"Project deleted: {project_id} by user {user_id}")
