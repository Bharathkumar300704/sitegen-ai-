"""
Download API routes — generate and serve ZIP files.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from repositories import generation_repository, project_repository
from services.download_service import create_website_zip
from auth.dependencies import get_current_user
from database.models.user import User

router = APIRouter(prefix="/api", tags=["Downloads"])


@router.get("/projects/{project_id}/download")
def download_project(project_id: str, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Download the generated website as a ZIP file."""
    # Verify project ownership
    project = project_repository.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get current website
    website = generation_repository.get_current_website(db, project_id)
    if not website:
        raise HTTPException(status_code=404, detail="No website generated yet")

    # Create ZIP
    zip_path = create_website_zip(
        project.name,
        website.html_content or "",
        website.css_content or "",
        website.js_content or "",
    )

    return FileResponse(
        path=zip_path,
        filename=f"{project.name.replace(' ', '-').lower()}.zip",
        media_type="application/zip",
    )
