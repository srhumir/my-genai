# GitHub Copilot Guidelines

These instructions guide Copilot to produce code that matches our repository style and practices.

## General Behavior
- Prefer concise, single-responsibility functions. Avoid combining unrelated logic.
- Declare types for all inputs/outputs. Use `dataclass` instead of dicts for structured data.
- Avoid commented-out code and unused imports/variables.
- Use comments only if really necessary. Prefer restructuring code for clarity over adding comments. 
- If comments are needed, suggest extracting into a function with a clear docstring.

## Formatting and Style
- Python: follow PEP 8 and format with `black`. Keep line lengths reasonable.
- Function/method names: lowercase with underscores, use verb-like names describing the action.
- Class/type names: CapWords (e.g., `SomeClass`).
- Constants: UPPER_CASE_WITH_UNDERSCORES at module level.
- Private methods: start with a leading underscore.

## Functions and APIs
- Keep argument count ≤ 3 when possible; otherwise bundle with a dataclass.
- Always annotate types explicitly. For empty variables, include type annotations.
- Suggest specific exception handling (avoid bare `except:`). Use `except Exception as e` and log.
- Use `assert` only for invariant checks that should never fail unless there’s a bug.
- Validate external data with `raise` on invalid states.

## Project Conventions
- Don’t introduce default parameter values unless needed for backward compatibility.
- Order functions in “reading order”: high-level entry points first, followed by helpers in usage order.
- If a project-wide constant is needed, use/create a `constants` module.

## Repository-specific Guidance
- Use LiteLLM types (e.g., `ChatCompletionToolParam`) when interacting with model/tooling.
- Chainlit: store agent instances in `cl.user_session.set` and reuse for message handling.
- Memory isolation: respect `correlation_id` per-call semantics; add/delete memory via RAM store with retention.
- MCP tools: agents expose `prepare_response(query: str) -> str`; register as tools for inter-agent calls.

## Documentation and Tests
- When editing public behavior, update docs (README) and add minimal tests (happy path + edge) under `tests/`.
- Keep changes small and focused; preserve existing public APIs unless explicitly refactoring.

## Security
- Avoid arbitrary code execution in replacements; prefer deterministic helpers.
- Don’t log secrets; use structured logging for errors.
