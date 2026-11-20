
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.sql import func

from app.database.connection import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=True)
    email = Column(String(320), nullable=True)
    company = Column(String(200), nullable=True)

    enquiry = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)

    # Human approval decision (kept for compatibility)
    approval_status = Column(
        String(30),
        default="Pending",
        nullable=False,
    )

    # Sales lifecycle tracking
    lifecycle_status = Column(
        String(30),
        default="New",
        nullable=False,
        index=True,
    )

    assigned_to = Column(String(200), nullable=True)

    review_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    converted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
