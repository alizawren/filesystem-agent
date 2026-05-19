"""Minimal tool-calling agent loop."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_DEFINITIONS, run_tool

SYSTEM_PROMPT = """You are a helpful workspace assistant.

You can inspect files with list_files and read_file, and save output with write_file.
Only state facts you found in the workspace. If information is missing, say so.

When asked for a standup or summary, use this format:
## Done
- bullet points

## Blockers
- bullet points (or "None")

## Next
- bullet points
"""


class Agent:
    def __init__(
        self,
        workspace: Path,
        *,
        model: str | None = None,
        max_steps: int = 8,
    ) -> None:
        load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY in .env (see .env.example)")

        self.workspace = workspace.resolve()
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.max_steps = max_steps
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def run(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(self.max_steps):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_DEFINITIONS,
            )
            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return message.content or ""

            for call in message.tool_calls:
                result = run_tool(
                    self.workspace,
                    call.function.name,
                    call.function.arguments,
                )
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        return "Stopped: reached max agent steps. Try a simpler question."
