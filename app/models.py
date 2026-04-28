from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)

    app_name = Column(String(50), unique=True, nullable=False, index=True)
    image = Column(String(150), nullable=False)

    host_port = Column(Integer, nullable=False)
    container_port = Column(Integer, nullable=False)

    memory_limit = Column(String(20), nullable=True)
    cpu_limit = Column(Float, nullable=True)

    health_path = Column(String(100), nullable=True, default="/")
    health_check_enabled = Column(Boolean, nullable=False, default=True)
    health_status = Column(String(30), nullable=True)

    container_id = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="created")

    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    action = Column(String(50), nullable=False)
    app_name = Column(String(50), nullable=True, index=True)

    status = Column(String(30), nullable=False)
    message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)