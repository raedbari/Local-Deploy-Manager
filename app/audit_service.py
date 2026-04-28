from sqlalchemy.orm import Session

from app import models


def create_audit_log(
    db: Session,
    action: str,
    status: str,
    app_name: str | None = None,
    message: str | None = None,
):
    log = models.AuditLog(
        action=action,
        app_name=app_name,
        status=status,
        message=message,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log