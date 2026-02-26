# my-genai
Chatbot the way I like it

# Overview
my-genai lets you define AI agents using simple YAML configs and automatically serves them in three ways:
- A Chainlit chat UI for human conversations.
- FastAPI endpoints so you can call each agent over HTTP.
- MCP tools so agents can call each other programmatically.
- Optional initial action prompts to quickly start common tasks in the UI.

You add agents by dropping a folder with `agent_config.yaml` and a `system_prompt.md` under `src/agents_library/agents/`. 
The app discovers them at startup and wires them into the UI, the API, and the MCP server.

# How it works (technical)
Below is a quick walkthrough of the main pieces.

- Agent definition
  - Location: `src/agents_library/agents/<agent_name>/`
  - Files:
    - `agent_config.yaml`: model name, temperature, allowed tools, description, etc. Supports `replace_variables`.
    - `system_prompt.md`: the agent’s system instructions (with variable placeholders like `{bot_user_name}`).
    - Optional `replacement_method.py`: provides a function `variables_to_replace_in_prompt(self)` to dynamically supply 
      values when `replace_variables` uses `...`.
    - Optional `initial_action_prompts.md`: Markdown file that defines quick-start actions for the UI.

- Initial action prompts
  - Class: `BaseAgent` (`src/agents_library/base.py`), method: `get_initial_action_prompts()`.
  - Reads `initial_action_prompts.md` from the agent folder, applies `_replace_variables_in_prompt`, and parses sections by headers:
    - Each line starting with `#` becomes a section key (header text without `#`).
    - All lines until the next `#` (or end of file) become the section value.
  - Returned as a dict: `{section_name: section_text}`.
  - The Chainlit frontend (`chainlit_frontend.py`) shows these as selectable actions at chat start. If the user
    chooses one of them. The agent receives the section text as a user message to kick off the conversation.

- Prompt building and tools section
  - Class: `BaseAgent` (`src/agents_library/base.py`).
  - Variable replacement:
    - Literal values come from `agent_config.yaml` under `replace_variables`.
    - If a value is `...`, `BaseAgent` tries to load `replacement_method.py` and call `variables_to_replace_in_prompt(self)` to get the value at runtime.
  - Tools section auto-update:
    - `get_system_prompt()` ensures a `## AVAILABLE TOOLS:` section contains short, first-line descriptions for the agent’s allowed tools.
    - If the section exists, new tool bullets are appended to it; if it’s missing and tools exist, the section is added at the end.

- Chat client and LiteLLM
  - Class: `ChatClient` (`src/api_client/chat_client.py`).
  - Wraps LiteLLM’s chat API and respects the agent’s config (model, tools, tool_choice, response_format).
  - Accepts messages and optional tools, returns the model response; errors like `BadRequestError` are handled by shrinking memory and retrying.

- Memory model (per-call isolation)
  - Each API call uses a `correlation_id` to keep memory isolated in RAM.
  - First call can omit the id; the server returns one to use for subsequent calls to continue the same context.
  - Memory can be deleted via an endpoint and is also cleaned up with a retention policy.

- Routers split
  - Directory: `routers/`
  - `chainlit_router.py`: mounts the Chainlit UI under `/chat` and initializes/stores the chosen agent instance in the Chainlit `user_session`.
  - `agents_router.py`: exposes `/api/agents/<agent_name>` endpoints and memory management routes.
  - Function definitions and schemas are separated per router module.

- Chainlit UI
  - File: `chainlit_frontend.py`.
  - On chat start, reads `?agent=<agent_name>`, instantiates `BaseAgent` from `AGENT_FOLDER_PATH`, and stores it in `cl.user_session.set()`.
  - On messages, forwards text to the stored agent and streams back replies.
  - If `initial_action_prompts.md` exists, shows them as quick-start actions.

- MCP server and inter-agent tools
  - File: `mcp_server/server.py`.
  - Registers each agent as an MCP tool so agents can call each other via MCP.
  - Each tool’s `prepare_response(query)` returns a string; these tools are stateless and don’t share memory.

- Tests
  - File: `tests/test_src/agent_library/test_base.py`.
  - Covers:
    - Updating an existing `## AVAILABLE TOOLS:` section.
    - Adding the tools section when missing.
    - Variable replacement for literals and dynamic values via `replacement_method.py`.
    - Parsing `initial_action_prompts.md` into sections and handling missing files.
# TODOs (ordered)
~~1. Tool descriptions in system prompt~~
   - Enumerate allowed tools per agent with short guidance so the model picks the right tool.
2. Persist memory (session-level)
   - Add TTL + delete endpoint (already exists) and optional disk/DB later. Define memory layers (session/topic/agent) and lifecycle.
~~3. Suggested initial action prompts per agent~~
   - Configurable hints to guide first steps for users and the model.
~~4. Replace_variables (safe subset)~~
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
