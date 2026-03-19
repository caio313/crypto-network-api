from sqlalchemy import Column, String, DateTime, Boolean, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ApiKey(Base):
    __tablename__ = "api_keys"

    key = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    tier = Column(String(10), nullable=False, default="free")
    __table_args__ = (
        CheckConstraint("tier IN ('free','pro','enterprise')", name="ck_api_keys_tier"),
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    requests_today = Column(String, default="0")
