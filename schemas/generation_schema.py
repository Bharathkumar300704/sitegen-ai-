"""
Pydantic schemas for website generation.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class GenerationRequest(BaseModel):
    """Schema for website generation request."""
    prompt: str
    project_id: Optional[str] = None
    website_type: Optional[str] = None


class GenerationResponse(BaseModel):
    """Schema for website generation response."""
    project_id: str
    website_id: str
    html: str
    css: str
    js: str
    detected_language: Optional[str] = None
    website_type: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None


class RegenerationRequest(BaseModel):
    """Schema for section regeneration."""
    project_id: str
    website_id: str
    section: str
    instructions: str


class WebsiteVersionResponse(BaseModel):
    """Schema for website version info."""
    id: str
    version: int
    is_current: bool
    created_at: datetime

    class Config:
        from_attributes = True
