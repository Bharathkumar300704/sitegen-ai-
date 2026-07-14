"""WebsiteRequest model — stores the user's prompt and AI analysis results."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base


class WebsiteRequest(Base):
    __tablename__ = "website_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    detected_language: Mapped[str] = mapped_column(String(50), nullable=True)
    analyzed_requirements: Mapped[str] = mapped_column(Text, nullable=True)  # JSON stored as text for SQLite
    website_plan: Mapped[str] = mapped_column(Text, nullable=True)  # JSON stored as text for SQLite
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="requests")
