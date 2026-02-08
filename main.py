import os
from logging import getLogger
from pathlib import Path

from chainlit.utils import mount_chainlit
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.agents_library.base import ChatSessionConfig
from src.agents_library.initiator import load_agents
from src.config.settings import settings

logger = getLogger(__name__)
app = FastAPI()
services: list[dict[str, str]] = []

mount_chainlit(app=app, target="./chainlit_frontend.py", path="/chat")
app.mount("/welcome", StaticFiles(directory="html", html=True), name="html")


def register_service(name: str, path: str, description: str) -> None:
    logger.info(f"Adding Chainlit service '{name}' at path '{path}'")
    services.append({"display_name": name, "name": path, "description": description})


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

base_path = Path("chainlit_frontend.py")

for agent in agents:
    register_service(
        name=agent.agent_settings.agent_config.name,
        path=f"{os.path.split(agent.agent_folder_path)[1]}",
        description=agent.agent_settings.agent_config.description,
    )
