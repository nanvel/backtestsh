from typing import Optional

from anthropic import Anthropic
from anthropic.types import TextBlock
from rich.console import Console
from rich.markdown import Markdown

from app.strategy import Strategy, StrategyFactory

SYSTEM_PROMPT = """You are a part of a chain of agents that backtests trading ideas,
your task is to provide a clear strategy description and backtest configuration based on the user's prompt.

If the user prompts does not contain a specific trading strategy, tell them that a strategy can not be derived from the prmpt provided.

If some pieces of backtest configuration are missing, pick up default values from the list:
- asset: Bitcoin (BTCUSDT)
- interval: 1 day (1d)
- timeframe: 500 intervals

If an exit condition is provided, do not use take-profit/stop-loss (unless mentioned explicitly).
Otherwise, if no exit condition is provided, use take-profit and stop-loss equal 1 ATR.

Generate a name for the strategy, up to 50 characters in length.

Example:
User: Buy on Friday and sell on Sunday
Your answer:
**Strategy Name:**
Buy on Friday and Sell on Sunday
**Strategy Description:**
A simple calendar-based trading strategy that enters long positions on Fridays and exits on Sundays, capitalizing on potential weekend market patterns or gaps.
**Entry Conditions:**
- Enter a long position (buy) at market open on Friday
- No additional technical or fundamental conditions required
**Exit Conditions:**
- Exit the long position (sell) at market open on Sunday
- This is a time-based exit condition, so no take-profit or stop-loss will be applied
**Backtest Configuration:**
- Asset: BTCUSDT (Bitcoin/USDT pair)
- Time Interval: 1 day
- Timeframe: 500 intervals

Example:
User: hi!
Your answer:
No specific trading strategy was provided in the prompt.
Since no strategy details were given, I cannot create a meaningful trading strategy from just "hi!".
A trading strategy requires at least entry conditions to be defined.
"""


class PromptExpander:
    """Expands user prompt into a strategy description."""

    def __init__(self, client: Anthropic, strategy_factory: StrategyFactory):
        self._client = client
        self._strategy_factory = strategy_factory

    def __call__(self, console: Console, prompt: Optional[str] = None) -> Strategy:
        message = prompt or console.input("Describe a trading strategy and I'll backtest it.\n→ ").strip()
        chat_history = [
            {
                "role": "user",
                "content": [TextBlock(text=message, type="text")],
            }
        ]
        while True:
            with console.status(""):
                response = self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    temperature=0.2,
                    system=SYSTEM_PROMPT,
                    messages=chat_history,
                )
            console.print(Markdown(response.content[0].text))
            strategy = self._strategy_factory.from_description(response.content[0].text)
            if strategy:
                return strategy
            chat_history.append({"role": "assistant", "content": response.content})
            while True:
                message = console.input("\n→ ").strip()
                if message:
                    chat_history.append({"role": "user", "content": [TextBlock(text=message, type="text")]})
                    break
