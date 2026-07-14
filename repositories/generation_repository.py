"""
Generation repository — database operations for website generation.
"""

import json
from sqlalchemy.orm import Session
from database.models.website_request import WebsiteRequest
from database.models.generated_website import GeneratedWebsite
from database.models.prompt_history import PromptHistory
from typing import List


def save_website_request(db: Session, project_id: str, prompt: str,
                         detected_language: str = None, requirements: dict = None,
                         plan: dict = None) -> WebsiteRequest:
    """Save a website generation request."""
    request = WebsiteRequest(
        project_id=project_id,
        original_prompt=prompt,
        detected_language=detected_language,
        analyzed_requirements=json.dumps(requirements) if requirements else None,
        website_plan=json.dumps(plan) if plan else None,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def save_generated_website(db: Session, project_id: str, request_id: str,
                           html: str, css: str, js: str, version: int = 1) -> GeneratedWebsite:
    """Save generated website code."""
    # Mark all previous versions as not current
    db.query(GeneratedWebsite).filter(
        GeneratedWebsite.project_id == project_id
    ).update({"is_current": False})

    website = GeneratedWebsite(
        project_id=project_id,
        request_id=request_id,
        html_content=html,
        css_content=css,
        js_content=js,
        version=version,
        is_current=True,
    )
    db.add(website)
    db.commit()
    db.refresh(website)
    return website


def get_current_website(db: Session, project_id: str) -> GeneratedWebsite | None:
    """Get the current (latest) version of a generated website."""
    return db.query(GeneratedWebsite).filter(
        GeneratedWebsite.project_id == project_id,
        GeneratedWebsite.is_current == True
    ).first()


def get_website_versions(db: Session, project_id: str) -> List[GeneratedWebsite]:
    """Get all versions of a generated website."""
    return db.query(GeneratedWebsite).filter(
        GeneratedWebsite.project_id == project_id
    ).order_by(GeneratedWebsite.version.desc()).all()


def get_website_by_id(db: Session, website_id: str) -> GeneratedWebsite | None:
    """Get a specific website by ID."""
    return db.query(GeneratedWebsite).filter(GeneratedWebsite.id == website_id).first()


def save_prompt_history(db: Session, user_id: str, project_id: str,
                        prompt_text: str, prompt_type: str = "generation",
                        response_summary: str = None) -> PromptHistory:
    """Save a prompt to history."""
    history = PromptHistory(
        user_id=user_id,
        project_id=project_id,
        prompt_text=prompt_text,
        prompt_type=prompt_type,
        response_summary=response_summary,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def get_prompt_history(db: Session, user_id: str, limit: int = 50) -> List[PromptHistory]:
    """Get user's prompt history."""
    return db.query(PromptHistory).filter(
        PromptHistory.user_id == user_id
    ).order_by(PromptHistory.created_at.desc()).limit(limit).all()


def get_next_version(db: Session, project_id: str) -> int:
    """Get the next version number for a project."""
    latest = db.query(GeneratedWebsite).filter(
        GeneratedWebsite.project_id == project_id
    ).order_by(GeneratedWebsite.version.desc()).first()
    return (latest.version + 1) if latest else 1
