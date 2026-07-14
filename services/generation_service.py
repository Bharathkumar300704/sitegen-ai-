"""
Generation service — orchestrates the full website generation pipeline.

Pipeline: User Prompt → Language Detection → Requirement Analysis →
          Website Planning → Code Generation → Save to Database

IMPORTANT: Critical API errors (quota exhausted, invalid key, auth failure)
are propagated all the way to the HTTP response so the user sees the real
error instead of a silent fallback to the template engine.
"""

import json
import re
from sqlalchemy.orm import Session
from ai.openrouter_client import generate_content
from prompts.system_prompts import (
    LANGUAGE_DETECTION_PROMPT,
    REQUIREMENT_ANALYSIS_PROMPT,
    WEBSITE_PLANNING_PROMPT,
    CODE_GENERATION_PROMPT,
    SECTION_REGENERATION_PROMPT,
)
from repositories import generation_repository, project_repository
from services.fallback_service import generate_fallback_website
from config.logging_config import get_logger

logger = get_logger(__name__)

# Tags that mean "the API key / project quota is the problem, not a transient bug"
_CRITICAL_ERROR_TAGS = [
    "QUOTA_EXCEEDED",
    "UNAUTHORIZED",
    "FORBIDDEN",
    "API_KEY_INVALID",
    "NOT_FOUND",
    "BAD_REQUEST",
]


def _is_critical_api_error(err_str: str) -> bool:
    return any(tag in err_str for tag in _CRITICAL_ERROR_TAGS)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from AI response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def _extract_code_sections(text: str) -> dict:
    """Extract HTML, CSS, and JS from delimited AI response."""
    html = css = js = ""

    if "===HTML_START===" in text:
        html = text.split("===HTML_START===")[1].split("===HTML_END===")[0].strip()
    if "===CSS_START===" in text:
        css = text.split("===CSS_START===")[1].split("===CSS_END===")[0].strip()
    if "===JS_START===" in text:
        js = text.split("===JS_START===")[1].split("===JS_END===")[0].strip()

    # No delimiters — strip markdown wrappers and treat whole response as HTML
    if not html and not css and not js:
        cleaned = text.strip()
        for prefix in ("```html\n", "```html", "```\n", "```"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        html = cleaned.strip()
        logger.warning("Code delimiters not found — treating full response as HTML")

    logger.info(f"_extract_code_sections: html={len(html)} css={len(css)} js={len(js)}")
    return {"html": html, "css": css, "js": js}


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────────────────────────────────────

def detect_language(prompt: str) -> dict:
    """Detect the language of the user's prompt."""
    try:
        response = generate_content(LANGUAGE_DETECTION_PROMPT.format(text=prompt))
        return _parse_json_response(response)
    except Exception as e:
        err_str = str(e)
        if _is_critical_api_error(err_str):
            raise   # propagate — don't silently continue
        logger.warning(f"Language detection non-critical failure: {e} — defaulting to English")
        return {"language": "English", "code": "en", "confidence": 0.5}


def analyze_requirements(prompt: str) -> dict:
    """Analyze user prompt to extract structured requirements."""
    try:
        response = generate_content(REQUIREMENT_ANALYSIS_PROMPT.format(prompt=prompt))
        return _parse_json_response(response)
    except Exception as e:
        err_str = str(e)
        if _is_critical_api_error(err_str):
            raise
        logger.warning(f"Requirement analysis non-critical failure: {e}")
        return {
            "website_type": "general",
            "sections": ["hero", "about", "contact"],
            "style": "modern",
            "content_summary": prompt,
        }


def create_website_plan(requirements: dict) -> dict:
    """Create a structured website plan from analyzed requirements."""
    try:
        response = generate_content(
            WEBSITE_PLANNING_PROMPT.format(requirements=json.dumps(requirements))
        )
        return _parse_json_response(response)
    except Exception as e:
        err_str = str(e)
        if _is_critical_api_error(err_str):
            raise
        logger.warning(f"Website planning non-critical failure: {e}")
        return {"title": "Website", "sections": [], "color_palette": {}}


def generate_website_code(plan: dict, original_prompt: str) -> dict:
    """Generate HTML, CSS, and JavaScript from the website plan."""
    logger.info(f"generate_website_code: prompt={original_prompt[:80]!r}")
    response = generate_content(
        CODE_GENERATION_PROMPT.format(
            plan=json.dumps(plan),
            original_prompt=original_prompt,
        )
    )
    logger.info(f"generate_website_code: raw response length={len(response)}")
    logger.info(f"generate_website_code: response head={response[:400]!r}")
    return _extract_code_sections(response)


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def generate_full_website(db: Session, user_id: str, prompt: str,
                          project_id: str = None) -> dict:
    """
    Full generation pipeline.  Critical API errors are re-raised (not swallowed)
    so the caller receives the real error instead of a silent fallback.
    """
    logger.info("=" * 70)
    logger.info("WEBSITE GENERATION PIPELINE START")
    logger.info(f"  User       : {user_id}")
    logger.info(f"  Prompt     : {prompt!r}")
    logger.info(f"  Prompt len : {len(prompt)} chars")
    logger.info(f"  Project ID : {project_id}")
    logger.info("=" * 70)

    # Step 1: Create / retrieve project
    if not project_id:
        project = project_repository.create_project(
            db, user_id,
            name=f"Website - {prompt[:50]}",
            description=prompt[:200],
        )
        project_id = project.id
    else:
        project = project_repository.get_project_by_id(db, project_id)
        if not project:
            raise ValueError("Project not found")

    project_repository.update_project(db, project, status="generating")

    fallback_used = False
    critical_error: Exception | None = None

    try:
        logger.info("Step 1/4: Detecting language ...")
        lang_info = detect_language(prompt)
        logger.info(f"  → {lang_info}")

        logger.info("Step 2/4: Analyzing requirements ...")
        requirements = analyze_requirements(prompt)
        logger.info(f"  → type={requirements.get('website_type')} sections={requirements.get('sections')}")

        logger.info("Step 3/4: Creating website plan ...")
        plan = create_website_plan(requirements)
        logger.info(f"  → title={plan.get('title')} sections={len(plan.get('sections', []))}")

        logger.info("Step 4/4: Generating website code ...")
        code = generate_website_code(plan, prompt)
        logger.info(
            f"  → HTML={len(code['html'])} CSS={len(code['css'])} JS={len(code['js'])} chars"
        )

        full_html = build_complete_html(code["html"], code["css"], code["js"])
        logger.info(f"AI pipeline SUCCEEDED — full_html={len(full_html)} chars")
        logger.info(f"full_html head: {full_html[:300]!r}")

        detected_language = lang_info.get("language")
        css_content = code["css"]
        js_content = code["js"]
        web_type = requirements.get("website_type", "general")

    except Exception as e:
        err_str = str(e)
        logger.error("=" * 70)
        logger.error("AI PIPELINE EXCEPTION")
        logger.error(f"  Type    : {type(e).__name__}")
        logger.error(f"  Message : {err_str}")
        logger.error("=" * 70)

        # Critical errors: surface them — don't silently fall back
        if _is_critical_api_error(err_str):
            critical_error = e
            project_repository.update_project(db, project, status="failed")
            raise RuntimeError(
                f"OpenRouter API error (not a code bug): {err_str}"
            ) from e

        # Non-critical (transient network, parse errors) → use template fallback
        logger.warning("Non-critical AI failure — using template fallback")
        fallback_used = True
        try:
            fallback = generate_fallback_website(prompt)
            requirements  = fallback["requirements"]
            plan          = fallback["plan"]
            full_html     = build_complete_html(fallback["html"], fallback["css"], fallback["js"])
            detected_language = fallback["detected_language"]
            css_content   = fallback["css"]
            js_content    = fallback["js"]
            web_type      = fallback["website_type"]
            logger.info(f"Fallback succeeded — html={len(full_html)} chars")
        except Exception as fe:
            project_repository.update_project(db, project, status="failed")
            logger.error(f"Fallback also failed: {fe}")
            raise e

    # Step 6: Persist to database
    try:
        request_rec = generation_repository.save_website_request(
            db, project_id, prompt,
            detected_language=detected_language,
            requirements=requirements,
            plan=plan,
        )
        version = generation_repository.get_next_version(db, project_id)
        website = generation_repository.save_generated_website(
            db, project_id, request_rec.id,
            html=full_html, css=css_content, js=js_content,
            version=version,
        )
        generation_repository.save_prompt_history(
            db, user_id, project_id, prompt,
            prompt_type="generation",
            response_summary=(
                f"Generated {web_type} website (Fallback)"
                if fallback_used
                else f"Generated {web_type} website via OpenRouter AI"
            ),
        )
        project_repository.update_project(
            db, project, status="completed", website_type=web_type
        )

        logger.info("=" * 70)
        logger.info(
            f"PIPELINE COMPLETE | project={project_id} v={version} "
            f"type={web_type} lang={detected_language} "
            f"fallback={fallback_used} html={len(full_html)}"
        )
        logger.info("=" * 70)

        return {
            "project_id":       project_id,
            "website_id":       website.id,
            "html":             full_html,
            "css":              css_content,
            "js":               js_content,
            "detected_language": detected_language,
            "website_type":     web_type,
            "plan":             plan,
            "version":          version,
            "fallback_used":    fallback_used,
        }

    except Exception as e:
        project_repository.update_project(db, project, status="failed")
        logger.error(f"Database save failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# HTML builder
# ─────────────────────────────────────────────────────────────────────────────

def build_complete_html(html: str, css: str, js: str) -> str:
    """Build a complete HTML document with embedded CSS and JS."""
    # Strip markdown fences AI sometimes adds
    html = html.strip()
    for prefix in ("```html\n", "```html", "```\n", "```"):
        if html.startswith(prefix):
            html = html[len(prefix):]
            break
    if html.endswith("```"):
        html = html[:-3]
    html = html.strip()

    h_lower = html.lower()
    if h_lower.startswith("<!doctype") or h_lower.startswith("<html"):
        # Already a complete document — embed CSS/JS if missing
        if css and "<style>" not in html:
            html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>", 1)
        if js and "<script>" not in html.split("</body>")[0] if "</body>" in html else True:
            html = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>", 1)
        return html

    # Partial HTML — wrap it
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Website</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
{css}
    </style>
</head>
<body>
{html}
    <script>
{js}
    </script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Section regeneration
# ─────────────────────────────────────────────────────────────────────────────

def regenerate_section(db: Session, user_id: str, project_id: str,
                       website_id: str, section: str, instructions: str) -> dict:
    """Regenerate a specific section of the website."""
    website = generation_repository.get_website_by_id(db, website_id)
    if not website:
        raise ValueError("Website not found")

    response = generate_content(
        SECTION_REGENERATION_PROMPT.format(
            current_html=website.html_content,
            section=section,
            instructions=instructions,
        )
    )

    code = _extract_code_sections(response)
    full_html = code["html"] if code["html"] else response

    version = generation_repository.get_next_version(db, project_id)
    new_website = generation_repository.save_generated_website(
        db, project_id, website.request_id,
        html=full_html,
        css=code.get("css", website.css_content),
        js=code.get("js", website.js_content),
        version=version,
    )
    generation_repository.save_prompt_history(
        db, user_id, project_id, instructions,
        prompt_type="regeneration",
        response_summary=f"Regenerated section: {section}",
    )

    return {
        "project_id": project_id,
        "website_id": new_website.id,
        "html":       full_html,
        "css":        code.get("css", website.css_content),
        "js":         code.get("js", website.js_content),
        "version":    version,
    }
