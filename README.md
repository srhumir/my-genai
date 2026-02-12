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
  - Other agents (or external MCP clients) can call these tools to collaborate or compose results. These tools 
    do not have integrated memory.

# TODOs (ordered)
1. Tool descriptions in system prompt
   - Enumerate allowed tools per agent with short guidance so the model picks the right tool.
2. Persist memory (session-level)
   - Add TTL + delete endpoint (already exists) and optional disk/DB later. Define memory layers (session/topic/agent) and lifecycle.
3. Suggested initial action prompts per agent
   - Configurable hints to guide first steps for users and the model.
4. Replace_variables (safe subset)
   - Support deterministic ops (dates, static config, lightweight lookups). Avoid arbitrary code for security.
5. Provide more specific example agents
   - E.g., Web Researcher, Code Assistant, Data Summarizer with clear boundaries and prompts.
6. Performance tweaks
   - Cache system_prompt per agent, lazy-load tools, avoid repeated file reads.

## Clarifications to add
- Document AgentConfig
  - Centralize LiteLLM settings, tools, response_format, and defaults. Validate required keys.
- Error handling expectations
  - Define failure modes and fallbacks: LLM BadRequest/timeouts, MCP call errors, missing prompts.
- Security and operations
  - Rate limiting and optional auth for public deployments. Avoid leaking sensitive config in logs.
- Type safety
  - Tighten types around LiteLLM params (e.g., ChatCompletionToolParam), message shapes, and response_format. Consider Protocols for tool schemas.

