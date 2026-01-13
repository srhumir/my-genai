from chainlit.utils import mount_chainlit
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

services: list[dict[str, str]] = []


def register_service(name: str, path: str, target: str) -> None:
    """Mounts a Chainlit service to the FastAPI app and registers its metadata.

    Args:
        name (str): Display name of the service.
        path (str): URL path where the service is mounted.
        target (str): Python file containing the Chainlit app.
    """
    mount_chainlit(app=app, target=target, path=path)
    services.append({"name": name, "path": path})


app.mount("/welcome", StaticFiles(directory="html", html=True), name="html")


@app.get("/api/services")
def list_services() -> dict[str, list[dict[str, str]]]:
    """List registered services as JSON for the guide page."""
    return {"services": services}


@app.get("/")
def root() -> RedirectResponse:
    """Redirect root to the HTML guide."""
    return RedirectResponse(url="/welcome/")


register_service(
    name="Service Engineer", path="/service_engineer", target="chainlit_service_engineer.py"
)
