import os
from logging import getLogger
from pathlib import Path

from fastapi import APIRouter

from src.agents_library import build_agent_settings
from src.agents_library.initiator import load_agent_paths
from src.config.settings import settings

logger = getLogger(__name__)
router = APIRouter()
services: list[dict[str, str]] = []


def register_agent_service(path: Path) -> None:
    agent_settings = build_agent_settings(settings, path / "agent_config.yaml")
    register_service(
        name=agent_settings.agent_config.name,
        path=f"{os.path.split(path)[1]}",
        description=agent_settings.agent_config.description,
    )


def register_service(name: str, path: str, description: str) -> None:
    logger.info(f"Adding Chainlit service '{name}' at path '{path}'")
    services.append({"display_name": name, "name": path, "description": description})


agent_paths = load_agent_paths()
for agent_path in agent_paths:
    register_agent_service(agent_path)


@router.get("/services")
def list_services() -> dict[str, list[dict[str, str]]]:
    """List registered services as JSON for the guide page."""
    return {"services": services}
