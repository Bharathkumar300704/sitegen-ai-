"""GeneratedWebsite model — stores generated HTML, CSS, and JavaScript."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base


class GeneratedWebsite(Base):
    __tablename__ = "generated_websites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("website_requests.id"), nullable=True)
    html_content: Mapped[str] = mapped_column(Text, nullable=True)
    css_content: Mapped[str] = mapped_column(Text, nullable=True)
    js_content: Mapped[str] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="websites")
