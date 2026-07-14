"""Import all models so SQLAlchemy and Alembic can discover them."""

from database.models.user import User
from database.models.project import Project
from database.models.website_request import WebsiteRequest
from database.models.generated_website import GeneratedWebsite
from database.models.prompt_history import PromptHistory
from database.models.user_preferences import UserPreferences

__all__ = [
    "User",
    "Project",
    "WebsiteRequest",
    "GeneratedWebsite",
    "PromptHistory",
    "UserPreferences",
]
