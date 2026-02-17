from pathlib import Path


def load_agent_paths(
    agents_root: str | Path | None = None,
) -> list[Path]:
    """List all the agents in library directory."""
    root = Path(agents_root) if agents_root else Path(__file__).parent / "agents"
    if not root.is_dir():
        raise FileNotFoundError(f"Agents root not found: {root}")

    agent_path_list: list[Path] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            agent_path_list.append(entry)

    return agent_path_list


if __name__ == "__main__":
    agents = load_agent_paths()
    for agent in agents:
        print(f"Loaded agent from: {agent}")
