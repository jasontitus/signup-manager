from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
