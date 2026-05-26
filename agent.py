"""Minimal tool-calling agent loop."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

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


def _build_tools() -> list[types.Tool]:
    declarations = [
        types.FunctionDeclaration(
            name=tool["function"]["name"],
            description=tool["function"]["description"],
            parameters_json_schema=tool["function"]["parameters"],
        )
        for tool in TOOL_DEFINITIONS
    ]
    return [types.Tool(function_declarations=declarations)]


class Agent:
    def __init__(
        self,
        workspace: Path,
        *,
        model: str | None = None,
        max_steps: int = 8,
    ) -> None:
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY in .env (see .env.example)")

        self.workspace = workspace.resolve()
        self.client = genai.Client(api_key=api_key)
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.max_steps = max_steps
        self.tools = _build_tools()
        self.contents: list[types.Content] = []

    def run(self, user_message: str) -> str:
        self.contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )
        config = types.GenerateContentConfig(
            tools=self.tools,
            system_instruction=SYSTEM_PROMPT,
        )

        for _ in range(self.max_steps):
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.contents,
                config=config,
            )

            if not response.function_calls:
                return response.text or ""

            if response.candidates and response.candidates[0].content:
                self.contents.append(response.candidates[0].content)

            tool_parts: list[types.Part] = []
            for call in response.function_calls:
                args = call.args or {}
                result = run_tool(
                    self.workspace,
                    call.name,
                    json.dumps(args),
                )
                tool_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"result": result},
                    )
                )
            self.contents.append(types.Content(role="tool", parts=tool_parts))

        return "Stopped: reached max agent steps. Try a simpler question."
