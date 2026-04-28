# Local Deploy Manager

A small local DevOps tool built with FastAPI to deploy and manage Docker containers through an API and a simple web UI.

The project is designed as a practical learning project for combining backend development with Docker automation, PostgreSQL, health checks, resource limits, and audit logs.

---

## Problem

Managing Docker containers manually can become repetitive and error-prone.

Common manual tasks include:

```bash
docker run
docker ps
docker logs
docker stop
docker restart
docker rm
```

This project provides a simple control layer to make these operations easier and more organized.

---

## What the Project Does

Local Deploy Manager allows users to:

- Deploy Docker containers
- Start, stop, restart, and delete containers
- View container logs
- Run HTTP health checks
- Apply CPU and memory limits
- Store deployment records in PostgreSQL
- Track actions using audit logs
- Use both REST API and Web UI

---

## Tech Stack

- Python
- FastAPI
- Docker SDK for Python
- PostgreSQL
- SQLAlchemy
- Jinja2 Templates
- HTML / CSS
- Docker Compose

---

## Main Features

### Deployment Management

Deploy a container by providing:

- App name
- Docker image
- Host port
- Container port
- Memory limit
- CPU limit
- Health check path

Example:

```json
{
  "app_name": "demo-nginx",
  "image": "nginx:latest",
  "host_port": 8085,
  "container_port": 80,
  "memory_limit": "256m",
  "cpu_limit": 0.5,
  "health_path": "/",
  "health_check_enabled": true
}
```

---

### Container Operations

Supported actions:

- Start
- Stop
- Restart
- Delete
- View logs
- Run health check

---

### Audit Logs

The system records important actions such as:

- deploy
- start
- stop
- restart
- delete
- health check

Each audit log stores:

- action
- app name
- status
- message
- timestamp

---

## Web UI

The project includes a simple web interface.

Pages:

- Dashboard
- Deploy Container
- Container Logs
- Audit Logs

Open the UI at:

```text
http://localhost:8000/ui
```

---

## API Docs

FastAPI automatically provides Swagger documentation.

```text
http://localhost:8000/docs
```

---

## Project Structure

```text
local-deploy-manager/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── docker_service.py
│   ├── audit_service.py
│   │
│   ├── routes/
│   │   ├── deployments.py
│   │   ├── audit_logs.py
│   │   └── pages.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── deploy.html
│   │   ├── logs.html
│   │   └── audit_logs.html
│   │
│   └── static/
│       └── style.css
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd local-deploy-manager
```

### 2. Create virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux / WSL:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

Create a file named:

```text
.env
```

Example:

```env
DATABASE_URL=postgresql://deploy_user:deploy_pass@localhost:5433/deploy_manager
```

### 5. Start PostgreSQL

```bash
docker compose up -d db
```

### 6. Run the application

```bash
uvicorn app.main:app --reload
```

---

## Docker Compose

Example PostgreSQL service:

```yaml
services:
  db:
    image: postgres:16
    container_name: local-deploy-manager-db
    environment:
      POSTGRES_DB: deploy_manager
      POSTGRES_USER: deploy_user
      POSTGRES_PASSWORD: deploy_pass
    ports:
      - "5433:5432"
    volumes:
      - deploy-manager-db-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  deploy-manager-db-data:
```

---

## Important Endpoints

```http
POST /api/deployments
GET /api/deployments
GET /api/deployments/docker
GET /api/deployments/{app_name}/logs
POST /api/deployments/{app_name}/start
POST /api/deployments/{app_name}/stop
POST /api/deployments/{app_name}/restart
DELETE /api/deployments/{app_name}
POST /api/deployments/{app_name}/health
GET /api/audit-logs
```
## Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Deploy Container
![Deploy](screenshots/deploy.png)

### Audit Logs
![Audit Logs](screenshots/audit_logs.png)

### API Docs
![API Docs](screenshots/api_docs.png)
---

## What I Learned

This project helped me practice:

- FastAPI backend development
- Docker automation with Python
- PostgreSQL integration
- SQLAlchemy models
- API design
- Container lifecycle management
- Health checks
- Resource limits
- Audit logging
- Building a simple internal DevOps tool

---

## Limitations

This project is still a local learning project.

Current limitations:

- No authentication
- No user roles
- No rollback
- No continuous monitoring
- No Alembic migrations
- No automated tests
- Not designed for production use

---

## Future Improvements

- Add authentication
- Add rollback support
- Add Prometheus and Grafana metrics
- Add Alembic migrations
- Add automated tests
- Add image whitelist
- Improve UI feedback and error handling

---

## Summary

Local Deploy Manager is a small local Docker control tool that combines backend development and DevOps automation.

It provides a simple way to deploy and manage Docker containers through FastAPI, PostgreSQL, and a basic web UI.
