"""
Generation API routes — website generation, preview, versions, and API status.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from schemas.generation_schema import GenerationRequest, RegenerationRequest
from services.generation_service import generate_full_website, regenerate_section
from repositories import generation_repository
from auth.dependencies import get_current_user
from database.models.user import User
from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Generation"])


@router.post("/generate")
def generate_website(
    data: GenerationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a complete website from a natural language prompt."""
    logger.info("=" * 70)
    logger.info("[/api/generate] INCOMING REQUEST")
    logger.info(f"  User       : {user.id}")
    logger.info(f"  Prompt     : {data.prompt!r}")
    logger.info(f"  Prompt len : {len(data.prompt)}")
    logger.info(f"  Project ID : {data.project_id}")
    logger.info("=" * 70)

    try:
        result = generate_full_website(db, user.id, data.prompt, project_id=data.project_id)
        logger.info(
            f"[/api/generate] DONE project={result.get('project_id')} "
            f"type={result.get('website_type')} html_len={len(result.get('html',''))} "
            f"fallback={result.get('fallback_used', False)}"
        )
        return result

    except ValueError as e:
        logger.error(f"[/api/generate] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except RuntimeError as e:
        err = str(e)
        logger.error(f"[/api/generate] RuntimeError: {err}")

        # Surface OpenRouter-specific errors with actionable messages
        if "QUOTA_EXCEEDED" in err or "RESOURCE_EXHAUSTED" in err:
            raise HTTPException(
                status_code=429,
                detail=(
                    "❌ OpenRouter rate limit or quota exceeded. "
                    "Check your usage at https://openrouter.ai/account "
                    "or switch to a different model by updating OPENROUTER_MODEL in .env."
                ),
            )
        elif "UNAUTHORIZED" in err:
            raise HTTPException(
                status_code=401,
                detail=(
                    "❌ OpenRouter API key is UNAUTHORIZED. "
                    "Get a valid key at https://openrouter.ai/keys "
                    "and update OPENROUTER_API_KEY in .env"
                ),
            )
        elif "FORBIDDEN" in err:
            raise HTTPException(
                status_code=403,
                detail=(
                    "❌ OpenRouter API key is FORBIDDEN or lacks access to the selected model. "
                    "Check your account at https://openrouter.ai/account"
                ),
            )
        else:
            raise HTTPException(status_code=500, detail=err)


@router.post("/regenerate-section")
def regenerate_website_section(
    data: RegenerationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate a specific section of the website."""
    try:
        result = regenerate_section(
            db, user.id, data.project_id, data.website_id,
            data.section, data.instructions,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/preview", response_class=HTMLResponse)
def preview_website(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the live preview HTML for a project."""
    website = generation_repository.get_current_website(db, project_id)
    if not website:
        raise HTTPException(status_code=404, detail="No website generated yet")
    return HTMLResponse(content=website.html_content)


@router.get("/projects/{project_id}/versions")
def list_versions(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all versions of a generated website."""
    versions = generation_repository.get_website_versions(db, project_id)
    return [
        {
            "id": v.id,
            "version": v.version,
            "is_current": v.is_current,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.get("/projects/{project_id}/code")
def get_website_code(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the raw code (HTML, CSS, JS) for a project."""
    website = generation_repository.get_current_website(db, project_id)
    if not website:
        raise HTTPException(status_code=404, detail="No website generated yet")
    return {
        "html":    website.html_content,
        "css":     website.css_content,
        "js":      website.js_content,
        "version": website.version,
    }


@router.get("/history")
def get_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's prompt history."""
    history = generation_repository.get_prompt_history(db, user.id)
    return [
        {
            "id":         h.id,
            "prompt":     h.prompt_text,
            "type":       h.prompt_type,
            "summary":    h.response_summary,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in history
    ]


@router.get("/status/ai")
def ai_status(user: User = Depends(get_current_user)):
    """
    Health-check endpoint: tests whether the configured OpenRouter API key
    can successfully call the chat/completions endpoint.
    """
    from ai.openrouter_client import check_api_key_status
    status = check_api_key_status()

    if not status.get("ok"):
        err = status.get("error", "")
        if "QUOTA_EXCEEDED" in err or "429" in err:
            status["fix"] = (
                "Your OpenRouter account has hit the rate limit. "
                "Check your usage at https://openrouter.ai/account "
                "or switch to a different free model via OPENROUTER_MODEL in .env."
            )
        elif "UNAUTHORIZED" in err or "401" in err:
            status["fix"] = (
                "API key is invalid. "
                "Create a new one at https://openrouter.ai/keys"
            )
        elif "FORBIDDEN" in err or "403" in err:
            status["fix"] = (
                "Your API key does not have access to the selected model. "
                "Check your account at https://openrouter.ai/account"
            )
        else:
            status["fix"] = "Check server logs for the full error details."

    return status
