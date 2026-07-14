"""
Pydantic schemas for project operations.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str
    description: Optional[str] = None
    website_type: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    website_type: Optional[str] = None


class ProjectResponse(BaseModel):
    """Schema for project in API responses."""
    id: str
    name: str
    description: Optional[str] = None
    website_type: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""
    projects: List[ProjectResponse]
    total: int
