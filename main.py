import os
from pathlib import Path

from chainlit.utils import mount_chainlit
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.agents_library.base import ChatSessionConfig
from src.agents_library.initiator import load_agents
from src.config.settings import settings

app = FastAPI()

services: list[dict[str, str]] = []


def register_service(name: str, path: str, target: str, description: str) -> None:
    """Mounts a Chainlit service to the FastAPI app and registers its metadata.

    Args:
        name (str): Display name of the service.
        path (str): URL path where the service is mounted.
        target (str): Python file containing the Chainlit app.
        description (str): Description of the service to show to user.
    """
    mount_chainlit(app=app, target=target, path=path)
    services.append({"name": name, "path": path, "description": description})


app.mount("/welcome", StaticFiles(directory="html", html=True), name="html")


@app.get("/api/services")
def list_services() -> dict[str, list[dict[str, str]]]:
    """List registered services as JSON for the guide page."""
    return {"services": services}


@app.get("/")
def root() -> RedirectResponse:
    """Redirect root to the HTML guide."""
    return RedirectResponse(url="/welcome/")


session_config = ChatSessionConfig(
    bot_user_name="TestBot",
    session_id="session_123",
    topic_id="topic_abc",
)

agents = load_agents(settings, session_config)

base_path = Path("./chainlit_pages/base.py")

for agent in agents:
    agent_name = agent.agent_settings.agent_config.name
    clean_name = agent_name.lower().replace(" ", "_")
    agent_path = agent.agent_folder_path
    target_file = Path(f"./chainlit_pages/{clean_name}.py")

    with open(base_path, encoding="utf-8") as f:
        content = f.read().replace("$AGENT", os.path.split(agent_path)[-1])
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)

    register_service(
        name=agent_name,
        path=f"/{clean_name}",
        target=f"./chainlit_pages/{clean_name}.py",
        description=agent.agent_settings.agent_config.description,
    )
