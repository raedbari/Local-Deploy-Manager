from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import audit_service, docker_service, models
from app.database import get_db
from app.schemas import DeploymentCreate, DeploymentResponse, DeploymentRead


router = APIRouter(
    prefix="/deployments",
    tags=["Deployments"],
)


def sync_deployment_status(deployment: models.Deployment, db: Session):
    try:
        docker_status = docker_service.get_container_status(deployment.app_name)

        if docker_status is None:
            deployment.status = "missing"
            deployment.health_status = "unknown"
        else:
            deployment.status = docker_status

        deployment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(deployment)

    except RuntimeError as e:
        deployment.last_error = str(e)
        deployment.updated_at = datetime.utcnow()
        db.commit()

    return deployment


@router.post("", response_model=DeploymentResponse)
def create_deployment(payload: DeploymentCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == payload.app_name)
        .first()
    )

    if existing:
        audit_service.create_audit_log(
            db=db,
            action="deploy",
            app_name=payload.app_name,
            status="failed",
            message="Deployment with this app_name already exists in database",
        )
        raise HTTPException(
            status_code=409,
            detail="Deployment with this app_name already exists in database",
        )

    if docker_service.container_exists(payload.app_name):
        audit_service.create_audit_log(
            db=db,
            action="deploy",
            app_name=payload.app_name,
            status="failed",
            message="A Docker container with this app_name already exists",
        )
        raise HTTPException(
            status_code=409,
            detail="A Docker container with this app_name already exists",
        )

    if not docker_service.is_port_available(payload.host_port):
        audit_service.create_audit_log(
            db=db,
            action="deploy",
            app_name=payload.app_name,
            status="failed",
            message=f"Host port {payload.host_port} is already in use",
        )
        raise HTTPException(
            status_code=409,
            detail=f"Host port {payload.host_port} is already in use",
        )

    deployment = models.Deployment(
        app_name=payload.app_name,
        image=payload.image,
        host_port=payload.host_port,
        container_port=payload.container_port,
        memory_limit=payload.memory_limit,
        cpu_limit=payload.cpu_limit,
        health_path=payload.health_path,
        health_check_enabled=payload.health_check_enabled,
        status="creating",
        health_status="unknown",
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    try:
        result = docker_service.deploy_container(
            app_name=payload.app_name,
            image=payload.image,
            host_port=payload.host_port,
            container_port=payload.container_port,
            memory_limit=payload.memory_limit,
            cpu_limit=payload.cpu_limit,
            health_path=payload.health_path or "/",
            health_check_enabled=payload.health_check_enabled,
        )

        deployment.container_id = result["container_id"]
        deployment.status = result["status"]
        deployment.health_status = result.get("health_status")
        deployment.last_error = None
        deployment.updated_at = datetime.utcnow()

        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="deploy",
            app_name=payload.app_name,
            status="success",
            message="Container deployed successfully",
        )

        return result

    except RuntimeError as e:
        deployment.status = "failed"
        deployment.health_status = "unknown"
        deployment.last_error = str(e)
        deployment.updated_at = datetime.utcnow()

        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="deploy",
            app_name=payload.app_name,
            status="failed",
            message=str(e),
        )

        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[DeploymentRead])
def get_deployments(db: Session = Depends(get_db)):
    deployments = (
        db.query(models.Deployment)
        .order_by(models.Deployment.id.desc())
        .all()
    )

    synced_deployments = []

    for deployment in deployments:
        synced_deployments.append(sync_deployment_status(deployment, db))

    return synced_deployments


@router.get("/docker")
def get_docker_containers():
    try:
        return docker_service.list_containers()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{app_name}", response_model=DeploymentRead)
def get_deployment(app_name: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == app_name)
        .first()
    )

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found in database")

    return sync_deployment_status(deployment, db)


@router.post("/{app_name}/health")
def check_health(app_name: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == app_name)
        .first()
    )

    if not deployment:
        audit_service.create_audit_log(
            db=db,
            action="health_check",
            app_name=app_name,
            status="failed",
            message="Deployment not found in database",
        )
        raise HTTPException(status_code=404, detail="Deployment not found in database")

    if not deployment.health_check_enabled:
        audit_service.create_audit_log(
            db=db,
            action="health_check",
            app_name=app_name,
            status="failed",
            message="Health check is disabled for this deployment",
        )
        raise HTTPException(
            status_code=400,
            detail="Health check is disabled for this deployment",
        )

    result = docker_service.check_http_health(
        host_port=deployment.host_port,
        health_path=deployment.health_path or "/",
    )

    deployment.health_status = result["health_status"]
    deployment.updated_at = datetime.utcnow()

    if result["health_status"] == "unhealthy":
        deployment.last_error = result.get("error")
    else:
        deployment.last_error = None

    db.commit()

    audit_service.create_audit_log(
        db=db,
        action="health_check",
        app_name=app_name,
        status=result["health_status"],
        message=result.get("error") or "Health check completed",
    )

    return result


@router.get("/{app_name}/logs")
def get_logs(app_name: str):
    try:
        return docker_service.get_container_logs(app_name)
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_name}/stop")
def stop(app_name: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == app_name)
        .first()
    )

    if not deployment:
        audit_service.create_audit_log(
            db=db,
            action="stop",
            app_name=app_name,
            status="failed",
            message="Deployment not found in database",
        )
        raise HTTPException(status_code=404, detail="Deployment not found in database")

    try:
        result = docker_service.stop_container(app_name)

        deployment.status = result["status"]
        deployment.health_status = "unknown"
        deployment.last_error = None
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="stop",
            app_name=app_name,
            status="success",
            message="Container stopped successfully",
        )

        return result

    except RuntimeError as e:
        deployment.last_error = str(e)
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="stop",
            app_name=app_name,
            status="failed",
            message=str(e),
        )

        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_name}/start")
def start(app_name: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == app_name)
        .first()
    )

    if not deployment:
        audit_service.create_audit_log(
            db=db,
            action="start",
            app_name=app_name,
            status="failed",
            message="Deployment not found in database",
        )
        raise HTTPException(status_code=404, detail="Deployment not found in database")

    try:
        result = docker_service.start_container(app_name)

        deployment.status = result["status"]
        deployment.health_status = "unknown"
        deployment.last_error = None
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="start",
            app_name=app_name,
            status="success",
            message="Container started successfully",
        )

        return result

    except RuntimeError as e:
        deployment.last_error = str(e)
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="start",
            app_name=app_name,
            status="failed",
            message=str(e),
        )

        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_name}/restart")
def restart(app_name: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == app_name)
        .first()
    )

    if not deployment:
        audit_service.create_audit_log(
            db=db,
            action="restart",
            app_name=app_name,
            status="failed",
            message="Deployment not found in database",
        )
        raise HTTPException(status_code=404, detail="Deployment not found in database")

    try:
        result = docker_service.restart_container(app_name)

        deployment.status = result["status"]
        deployment.health_status = "unknown"
        deployment.last_error = None
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="restart",
            app_name=app_name,
            status="success",
            message="Container restarted successfully",
        )

        return result

    except RuntimeError as e:
        deployment.last_error = str(e)
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="restart",
            app_name=app_name,
            status="failed",
            message=str(e),
        )

        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{app_name}")
def delete(app_name: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(models.Deployment)
        .filter(models.Deployment.app_name == app_name)
        .first()
    )

    if not deployment:
        audit_service.create_audit_log(
            db=db,
            action="delete",
            app_name=app_name,
            status="failed",
            message="Deployment not found in database",
        )
        raise HTTPException(status_code=404, detail="Deployment not found in database")

    try:
        result = docker_service.delete_container(app_name)

        db.delete(deployment)
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="delete",
            app_name=app_name,
            status="success",
            message="Container deleted successfully",
        )

        return result

    except RuntimeError as e:
        deployment.last_error = str(e)
        deployment.updated_at = datetime.utcnow()
        db.commit()

        audit_service.create_audit_log(
            db=db,
            action="delete",
            app_name=app_name,
            status="failed",
            message=str(e),
        )

        raise HTTPException(status_code=404, detail=str(e))