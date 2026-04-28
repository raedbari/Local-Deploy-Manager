from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import models
from app.database import Base, engine
from app.routes.deployments import router as deployments_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.pages import router as pages_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Local Deploy Manager",
    description="A local DevOps tool to deploy and manage Docker containers through an API.",
    version="0.6.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(deployments_router, prefix="/api")
app.include_router(audit_logs_router, prefix="/api")
app.include_router(pages_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "local-deploy-manager",
        "version": "0.6.0",
    }