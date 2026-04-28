import socket
import time

import docker
import requests
from docker.errors import APIError, DockerException, NotFound


client = docker.from_env()


def is_port_available(host_port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", host_port))
        return result != 0


def container_exists(container_name: str) -> bool:
    try:
        client.containers.get(container_name)
        return True
    except NotFound:
        return False
    except DockerException as e:
        raise RuntimeError(f"Docker error while checking container: {str(e)}")


def get_container_status(container_name: str) -> str | None:
    try:
        container = client.containers.get(container_name)
        container.reload()
        return container.status
    except NotFound:
        return None
    except DockerException as e:
        raise RuntimeError(f"Docker error while getting status: {str(e)}")


def check_http_health(
    host_port: int,
    health_path: str = "/",
    retries: int = 5,
    delay: int = 2,
):
    if not health_path.startswith("/"):
        health_path = "/" + health_path

    url = f"http://localhost:{host_port}{health_path}"

    last_error = None

    for _ in range(retries):
        try:
            response = requests.get(url, timeout=2)

            if response.status_code == 200:
                return {
                    "health_status": "healthy",
                    "url": url,
                    "status_code": response.status_code,
                }

            last_error = f"Unexpected status code: {response.status_code}"

        except requests.RequestException as e:
            last_error = str(e)

        time.sleep(delay)

    return {
        "health_status": "unhealthy",
        "url": url,
        "error": last_error,
    }


def deploy_container(
    app_name: str,
    image: str,
    host_port: int,
    container_port: int,
    memory_limit: str = "256m",
    cpu_limit: float = 0.5,
    health_path: str = "/",
    health_check_enabled: bool = True,
):
    try:
        if container_exists(app_name):
            raise RuntimeError("A Docker container with this name already exists")

        if not is_port_available(host_port):
            raise RuntimeError(f"Host port {host_port} is already in use")

        nano_cpus = int(cpu_limit * 1_000_000_000)

        container = client.containers.run(
            image=image,
            name=app_name,
            ports={f"{container_port}/tcp": host_port},
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            mem_limit=memory_limit,
            nano_cpus=nano_cpus,
            labels={
                "managed-by": "local-deploy-manager",
                "app-name": app_name,
            },
        )

        container.reload()

        health_status = None

        if health_check_enabled:
            health_result = check_http_health(
                host_port=host_port,
                health_path=health_path,
            )
            health_status = health_result["health_status"]

        return {
            "message": "Container deployed successfully",
            "app_name": app_name,
            "container_id": container.id[:12],
            "status": container.status,
            "url": f"http://localhost:{host_port}",
            "health_status": health_status,
        }

    except APIError as e:
        raise RuntimeError(f"Docker API error: {e.explanation}")

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")


def list_containers():
    try:
        containers = client.containers.list(all=True)

        result = []

        for container in containers:
            container.reload()

            image = "unknown"
            if container.image.tags:
                image = container.image.tags[0]

            result.append({
                "id": container.id[:12],
                "name": container.name,
                "image": image,
                "status": container.status,
                "labels": container.labels,
            })

        return result

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")


def get_container_logs(container_name: str):
    try:
        container = client.containers.get(container_name)
        logs = container.logs(tail=100).decode("utf-8", errors="replace")

        return {
            "container": container_name,
            "logs": logs
        }

    except NotFound:
        raise RuntimeError("Container not found")

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")


def stop_container(container_name: str):
    try:
        container = client.containers.get(container_name)
        container.stop()

        container.reload()

        return {
            "message": "Container stopped successfully",
            "container": container_name,
            "status": container.status,
        }

    except NotFound:
        raise RuntimeError("Container not found")

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")


def start_container(container_name: str):
    try:
        container = client.containers.get(container_name)
        container.start()

        container.reload()

        return {
            "message": "Container started successfully",
            "container": container_name,
            "status": container.status,
        }

    except NotFound:
        raise RuntimeError("Container not found")

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")


def restart_container(container_name: str):
    try:
        container = client.containers.get(container_name)
        container.restart()

        container.reload()

        return {
            "message": "Container restarted successfully",
            "container": container_name,
            "status": container.status,
        }

    except NotFound:
        raise RuntimeError("Container not found")

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")


def delete_container(container_name: str):
    try:
        container = client.containers.get(container_name)
        container.remove(force=True)

        return {
            "message": "Container deleted successfully",
            "container": container_name,
        }

    except NotFound:
        raise RuntimeError("Container not found")

    except DockerException as e:
        raise RuntimeError(f"Docker error: {str(e)}")