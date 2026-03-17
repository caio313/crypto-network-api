from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()


class TierEnum(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class ApiKey(Base):
    __tablename__ = "api_keys"

    key = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    tier = Column(Enum(TierEnum), nullable=False, default=TierEnum.free)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    requests_today = Column(String, default="0")
