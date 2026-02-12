# my-genai
Chatbot the way I like it

# Overview
my-genai lets you define AI agents using simple YAML configs and automatically serves them in three ways:
- A Chainlit chat UI for human conversations.
- FastAPI endpoints so you can call each agent over HTTP.
- MCP tools so agents can call each other programmatically.

You add agents by dropping a folder with `agent_config.yaml` and a `system_prompt.md` under `src/agents_library/agents/`. The app discovers them at startup and wires them into the UI, the API, and the MCP server.

# How it works (technical)
Below is a quick walkthrough of the main pieces and data flow.

- Agent definition
  - Location: `src/agents_library/agents/<agent_name>/`
  - Files:
    - `agent_config.yaml`: model name, temperature, allowed tools, description, etc.
    - `system_prompt.md`: the agent’s system instructions (with optional variable replacements).

- Backend app
  - Entry: `main.py`
  - Discovers agent folders via `load_agent_paths()` and registers two interfaces:
    - Chainlit frontend at `/chat` (see `chainlit_frontend.py`). You can pass `?agent=<agent_name>` to chat with a specific agent.
    - HTTP API under `/api/agents/<agent_name>` for programmatic calls. Each POST takes `{ query, correlation_id? }` and returns `{ response, correlation_id }`.
  - Per-session memory: each call uses a `correlation_id` to isolate memory in RAM. If not provided, the server generates one and returns it. You can delete memory via `DELETE /api/agents/memory/{agent_key}/{correlation_id}`. There’s also automatic retention cleanup.

- Chainlit UI
  - File: `chainlit_frontend.py`
  - On chat start, it reads the `agent` query param, instantiates that agent, and stores the instance in the Chainlit user session.
  - On messages, it forwards text to the agent and streams back the reply.

- Agent runtime
  - Class: `BaseAgent` (`src/agents_library/base.py`)
  - Responsibilities:
    - Build the system prompt and conversation messages from memory.
    - Call the LLM via `ChatClient` using LiteLLM (supports tools and structured responses).
    - If the LLM requests tools, it runs them via `MCPClient`, adds tool results to memory, and calls the LLM again to finalize the answer.

- MCP server
  - File: `mcp_server/server.py`
  - Exposes each agent as an MCP tool (name + description from `agent_config.yaml`).
  - Other agents (or external MCP clients) can call these tools to collaborate or compose results.

# TODOs
* add tool description to the system prompt
* support replace_variables to run some code. For instance calling some tool, or getting current date etc.
* Support providing a list of suggested initial action prompts.
* have a more specific agent
* Persist memory
  * Define different levels of memory. session, topic, agent. For user or between users
* ~~Have a mcp server~~
* ~~Make websearch available~~
