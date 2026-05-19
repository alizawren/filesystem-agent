"""CLI entry point for the workspace agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Basic workspace agent")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Summarize what is in this workspace and write standup.md.",
        help="What you want the agent to do",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("sample"),
        help="Directory the agent may read/write (default: sample/)",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Workspace not found: {workspace}")

    agent = Agent(workspace)
    print(agent.run(args.prompt), end="")


if __name__ == "__main__":
    main()
