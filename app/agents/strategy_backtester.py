import random
import string
from pathlib import Path
from typing import Literal, Optional

from anthropic import Anthropic
from anthropic.types import TextBlock, ToolUseBlock
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown

from app.strategy import Strategy
from app.tools import RunBacktestTool, NewStrategyTool, SaveCodeTool

SYSTEM_PROMPT = """You are a quant coder specialized in backtesting trading strategies.
You will be provided with a trading strategy description.
Your task is to:
- code a strategy based on the description using the cipher library (documentation will be provided)
- run the backtest (use `write_code` and then `run_backtest` tools)
- fix any errors that may occur during the backtest
- summarize the backtest results
- assist the user with strategy tuning, if asked
"""


class StrategyBacktester:
    def __init__(self, client: Anthropic, root_path: Path, framework_docs: str):
        self._client = client
        self._root_path = root_path
        self._framework_docs = framework_docs

    def __call__(self, console: Console, strategy: Strategy) -> Optional[str]:
        chat_history = [
            {"role": "user", "content": [TextBlock(text=strategy.description, type="text")]},
            {"role": "user", "content": [TextBlock(text=self._framework_docs, type="text")]},
        ]
        if strategy.filepath.exists():
            tool_use_id = f"toolu_{''.join(random.choices(string.ascii_letters + string.digits, k=24))}"
            chat_history.append(
                {
                    "role": "assistant",
                    "content": [
                        TextBlock(
                            text=f'Now I\'ll implement the "{strategy.name}" strategy according to your specifications:',
                            type="text",
                        ),
                        ToolUseBlock(
                            id=tool_use_id,
                            input={"content": strategy.filepath.read_text()},
                            name="save_code",
                            type="tool_use",
                        ),
                    ],
                }
            )
            chat_history.append(
                {
                    "role": "user",
                    "content": [ToolResultBlock(content="SAVED", tool_use_id=tool_use_id, type="tool_result")],
                }
            )

        tools = [
            RunBacktestTool(file_path=strategy.filepath, root_path=self._root_path),
            SaveCodeTool(file_path=strategy.filepath, root_path=self._root_path),
            NewStrategyTool(),
        ]
        tools_map = {t.name: t for t in tools}
        while True:
            with console.status(""):
                response = self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=10000,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    messages=chat_history,
                    tools=[t.schema for t in tools],
                )
            chat_history.append({"role": "assistant", "content": response.content})
            had_tool_call = False
            for block in response.content:
                if block.type == "text":
                    console.print("\n")
                    console.print(Markdown(block.text))
                elif block.type == "tool_use":
                    had_tool_call = True
                    tool = tools_map[block.name]
                    tool_response = tool.execute(**block.input)

                    if isinstance(tool, NewStrategyTool):
                        console.clear()
                        return tool_response
                    if isinstance(tool_response, SaveCodeTool):
                        self._set_code(chat_history=chat_history, code=strategy.filepath.read_text())

                    console.print(tool_response)
                    chat_history.append(
                        {
                            "role": "user",
                            "content": [
                                ToolResultBlock(content=tool_response, tool_use_id=block.id, type="tool_result")
                            ],
                        }
                    )
            if had_tool_call:
                continue

            console.print("\n")

            while True:
                message = console.input(f"[dark_turquoise]{strategy.filepath.stem}.py[/dark_turquoise]\n→ ").strip()

                if message == "/chart":
                    RunBacktestTool(file_path=strategy.filepath, root_path=self._root_path).execute(plot_to_file=False)
                    continue
                elif message == "/new":
                    console.clear()
                    return None

                if message:
                    self._set_code(chat_history=chat_history, code=strategy.filepath.read_text())
                    chat_history.append({"role": "user", "content": [TextBlock(text=message, type="text")]})
                    break

    def _set_code(self, chat_history: list, code: str):
        """Updates the latest code block."""
        for message in reversed(chat_history):
            for block in message["content"]:
                if block.type == "tool_use" and block.name == "save_code":
                    block.input["content"] = code
                    return


class ToolResultBlock(BaseModel):
    content: str
    tool_use_id: str
    type: Literal["tool_result"]
