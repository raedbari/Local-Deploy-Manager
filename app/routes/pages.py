from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sqlalchemy.orm import Session

from app import docker_service, models
from app.database import get_db
from app.routes.deployments import sync_deployment_status
from app.schemas import DeploymentCreate
from app.routes import deployments as deployment_routes


router = APIRouter(
    prefix="/ui",
    tags=["Web UI"],
)

templates = Jinja2Templates(directory="app/templates")


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    deployments = (
        db.query(models.Deployment)
        .order_by(models.Deployment.id.desc())
        .all()
    )

    synced = []

    for deployment in deployments:
        synced.append(sync_deployment_status(deployment, db))

    running_count = len([d for d in synced if d.status == "running"])
    failed_count = len([d for d in synced if d.status == "failed"])
    healthy_count = len([d for d in synced if d.health_status == "healthy"])
    audit_count = db.query(models.AuditLog).count()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "deployments": synced,
            "running_count": running_count,
            "failed_count": failed_count,
            "healthy_count": healthy_count,
            "audit_count": audit_count,
        },
    )


@router.get("/deploy")
def deploy_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="deploy.html",
        context={},
    )


@router.post("/deploy")
def deploy_submit(
    app_name: str = Form(...),
    image: str = Form(...),
    host_port: int = Form(...),
    container_port: int = Form(...),
    memory_limit: str = Form("256m"),
    cpu_limit: float = Form(0.5),
    health_path: str = Form("/"),
    health_check_enabled: bool = Form(False),
    db: Session = Depends(get_db),
):
    payload = DeploymentCreate(
        app_name=app_name,
        image=image,
        host_port=host_port,
        container_port=container_port,
        memory_limit=memory_limit,
        cpu_limit=cpu_limit,
        health_path=health_path,
        health_check_enabled=health_check_enabled,
    )

    try:
        deployment_routes.create_deployment(payload=payload, db=db)
    except HTTPException:
        pass

    return RedirectResponse(
        url="/ui",
        status_code=303,
    )


@router.post("/{app_name}/start")
def ui_start(app_name: str, db: Session = Depends(get_db)):
    try:
        deployment_routes.start(app_name=app_name, db=db)
    except HTTPException:
        pass

    return RedirectResponse(url="/ui", status_code=303)


@router.post("/{app_name}/stop")
def ui_stop(app_name: str, db: Session = Depends(get_db)):
    try:
        deployment_routes.stop(app_name=app_name, db=db)
    except HTTPException:
        pass

    return RedirectResponse(url="/ui", status_code=303)


@router.post("/{app_name}/restart")
def ui_restart(app_name: str, db: Session = Depends(get_db)):
    try:
        deployment_routes.restart(app_name=app_name, db=db)
    except HTTPException:
        pass

    return RedirectResponse(url="/ui", status_code=303)


@router.post("/{app_name}/delete")
def ui_delete(app_name: str, db: Session = Depends(get_db)):
    try:
        deployment_routes.delete(app_name=app_name, db=db)
    except HTTPException:
        pass

    return RedirectResponse(url="/ui", status_code=303)


@router.post("/{app_name}/health")
def ui_health(app_name: str, db: Session = Depends(get_db)):
    try:
        deployment_routes.check_health(app_name=app_name, db=db)
    except HTTPException:
        pass

    return RedirectResponse(url="/ui", status_code=303)

@router.get("/audit/logs")
def audit_logs_page(request: Request, db: Session = Depends(get_db)):
    logs = (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.id.desc())
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="audit_logs.html",
        context={
            "logs": logs,
        },
    )

@router.get("/{app_name}/logs")
def logs_page(app_name: str, request: Request):
    try:
        result = docker_service.get_container_logs(app_name)
        logs = result["logs"]
    except RuntimeError as e:
        logs = str(e)

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "app_name": app_name,
            "logs": logs,
        },
    )


