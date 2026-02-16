from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.memory import ConversationMemory
from src.config.settings import settings


@pytest.mark.asyncio
async def test_get_system_prompt_updates_existing_tools_section(tmp_path: Path):
    agent_dir = tmp_path / "agents" / "demo_agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent_config.yaml").write_text(
        """
name: Demo Agent
description: Demo
model: openai/gpt-4o
replace_variables:
  bot_user_name: "Alice"
""",
        encoding="utf-8",
    )

    # Existing prompt with AVAILABLE TOOLS section and variable
    (agent_dir / "system_prompt.md").write_text(
        """
## ROLE & CONTEXT:
Demo role.

## USER & SYSTEM CONTEXT:
Name of the user: {bot_user_name}

## AVAILABLE TOOLS:
Existing line
""",
        encoding="utf-8",
    )

    agent = BaseAgent(
        settings=settings,
        session_config=ChatSessionConfig(
            bot_user_name="Alice", session_id="s", topic_id="t"
        ),
        memory=ConversationMemory(),
        agent_folder_path=agent_dir,
    )

    async def mock_get_tools(self: Any):
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_engine",
                    "description": "Search the web for relevant info\nMore details",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            }
        ]

    with patch.object(BaseAgent, "get_tools", new=mock_get_tools):
        content = await agent.get_system_prompt()

    assert "Name of the user: Alice" in content
    # Tools section should include existing line and appended tool description
    assert "## AVAILABLE TOOLS:" in content
    assert "Existing line" in content
    assert "* search_engine: Search the web for relevant info" in content


@pytest.mark.asyncio
async def test_get_system_prompt_adds_tools_section_when_missing(tmp_path: Path):
    agent_dir = tmp_path / "agents" / "demo_agent2"
    agent_dir.mkdir(parents=True)

    # agent config
    (agent_dir / "agent_config.yaml").write_text(
        """
name: Demo Agent 2
description: Demo2
model: openai/gpt-4o
""",
        encoding="utf-8",
    )

    (agent_dir / "system_prompt.md").write_text(
        """
## ROLE & CONTEXT:
Demo role.
""",
        encoding="utf-8",
    )

    agent = BaseAgent(
        settings=settings,
        session_config=ChatSessionConfig(
            bot_user_name="Bob", session_id="s2", topic_id="t2"
        ),
        memory=ConversationMemory(),
        agent_folder_path=agent_dir,
    )

    async def mock_get_tools2(self: Any):
        return [
            {
                "type": "function",
                "function": {
                    "name": "calc",
                    "description": "Compute things\nExtra",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

    with patch.object(BaseAgent, "get_tools", new=mock_get_tools2):
        content = await agent.get_system_prompt()

    assert content.strip().endswith("* calc: Compute things")
    assert "## AVAILABLE TOOLS:" in content


@pytest.mark.asyncio
async def test_replace_variables_literal_values(tmp_path: Path):
    agent_dir = tmp_path / "agents" / "literal_agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent_config.yaml").write_text(
        """
name: Literal Agent
description: Demo literal
model: openai/gpt-4o
replace_variables:
  hello: "Hi"
  bot_user_name: "Bob"
""",
        encoding="utf-8",
    )

    (agent_dir / "system_prompt.md").write_text(
        """
## ROLE & CONTEXT:
{hello} {bot_user_name}
""",
        encoding="utf-8",
    )

    agent = BaseAgent(
        settings=settings,
        session_config=ChatSessionConfig(
            bot_user_name="Ignored", session_id="s", topic_id="t"
        ),
        memory=ConversationMemory(),
        agent_folder_path=agent_dir,
    )

    content = await agent.get_system_prompt()
    assert "Hi Bob" in content


@pytest.mark.asyncio
async def test_replace_variables_dynamic_via_replacement_method(tmp_path: Path):
    agent_dir = tmp_path / "agents" / "dynamic_agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent_config.yaml").write_text(
        """
name: Dynamic Agent
description: Demo dynamic
model: openai/gpt-4o
replace_variables:
  bot_user_name: "..."
""",
        encoding="utf-8",
    )

    (agent_dir / "system_prompt.md").write_text(
        """
## USER & SYSTEM CONTEXT:
User: {bot_user_name}
""",
        encoding="utf-8",
    )

    # Provide replacement_method.py with variables_to_replace_in_prompt
    (agent_dir / "replacement_method.py").write_text(
        """
from src.agents_library.base import BaseAgent

def variables_to_replace_in_prompt(self: BaseAgent) -> dict[str, str]:
    return {"bot_user_name": self.session_config.bot_user_name}
""",
        encoding="utf-8",
    )

    agent = BaseAgent(
        settings=settings,
        session_config=ChatSessionConfig(
            bot_user_name="Alice", session_id="s", topic_id="t"
        ),
        memory=ConversationMemory(),
        agent_folder_path=agent_dir,
    )

    content = await agent.get_system_prompt()
    assert "User: Alice" in content


@pytest.mark.asyncio
async def test_get_initial_action_prompts_parses_sections(tmp_path: Path):
    agent_dir = tmp_path / "agents" / "init_prompts_agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent_config.yaml").write_text(
        """
name: Init Prompts Agent
description: Tests
model: openai/gpt-4o
replace_variables:
  who: "Alice"
""",
        encoding="utf-8",
    )

    (agent_dir / "initial_action_prompts.md").write_text(
        """
# Greeting
Hello {who}!

# Task
Please do X, Y, and Z.
With details on each step.

# Footer
Thanks.
""",
        encoding="utf-8",
    )

    agent = BaseAgent(
        settings=settings,
        session_config=ChatSessionConfig(
            bot_user_name="Bob", session_id="s", topic_id="t"
        ),
        memory=ConversationMemory(),
        agent_folder_path=agent_dir,
    )

    sections = await agent.get_initial_action_prompts()
    assert "Greeting" in sections
    assert "Task" in sections
    assert "Footer" in sections

    assert sections["Greeting"] == "Hello Alice!"
    assert sections["Task"].startswith("Please do X, Y, and Z.")
    assert "details on each step." in sections["Task"]
    assert sections["Footer"] == "Thanks."


@pytest.mark.asyncio
async def test_get_initial_action_prompts_missing_file_returns_empty_dict(
    tmp_path: Path,
):
    agent_dir = tmp_path / "agents" / "no_init_prompts_agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent_config.yaml").write_text(
        """
name: No Init Prompts Agent
description: Tests
model: openai/gpt-4o
""",
        encoding="utf-8",
    )

    agent = BaseAgent(
        settings=settings,
        session_config=ChatSessionConfig(
            bot_user_name="Bob", session_id="s", topic_id="t"
        ),
        memory=ConversationMemory(),
        agent_folder_path=agent_dir,
    )

    sections = await agent.get_initial_action_prompts()
    assert sections == {}
