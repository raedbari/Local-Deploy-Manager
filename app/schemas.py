from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeploymentCreate(BaseModel):
    app_name: str = Field(..., min_length=3, max_length=50)
    image: str = Field(..., min_length=2, max_length=150)

    host_port: int = Field(..., ge=1024, le=65535)
    container_port: int = Field(..., ge=1, le=65535)

    memory_limit: str = Field(default="256m", min_length=2, max_length=20)
    cpu_limit: float = Field(default=0.5, gt=0, le=4)

    health_path: Optional[str] = Field(default="/")
    health_check_enabled: bool = Field(default=True)


class DeploymentResponse(BaseModel):
    message: str
    app_name: str
    container_id: str
    status: str
    url: str
    health_status: Optional[str] = None


class DeploymentRead(BaseModel):
    id: int
    app_name: str
    image: str
    host_port: int
    container_port: int

    memory_limit: Optional[str]
    cpu_limit: Optional[float]

    health_path: Optional[str]
    health_check_enabled: bool
    health_status: Optional[str]

    container_id: Optional[str]
    status: str
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AuditLogRead(BaseModel):
    id: int
    action: str
    app_name: Optional[str]
    status: str
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True