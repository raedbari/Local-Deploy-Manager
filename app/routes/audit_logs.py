from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import AuditLogRead


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get("", response_model=list[AuditLogRead])
def get_audit_logs(
    app_name: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(models.AuditLog)

    if app_name:
        query = query.filter(models.AuditLog.app_name == app_name)

    logs = (
        query
        .order_by(models.AuditLog.id.desc())
        .limit(limit)
        .all()
    )

    return logs