from pathlib import Path

import pytest

from app.strategy import StrategyFactory


SUCCESS_RESPONSE = """**Strategy Name:**
Golden Cross Moving Average Crossover (1)

**Strategy Description:**
A classic trend-following strategy that enters long positions when the 50-period moving average crosses above the 200-period moving average
(golden cross), signaling a potential bullish trend reversal or continuation.

**Entry Conditions:**
- Enter a long position when the 50-period simple moving average crosses above the 200-period simple moving average
- This crossover event is known as a "golden cross" and typically indicates bullish momentum

**Exit Conditions:**
- Take-profit: Exit when price moves 1 ATR (Average True Range) above the entry price
- Stop-loss: Exit when price moves 1 ATR below the entry price
- ATR period: 14 (standard default)

**Backtest Configuration:**
- Asset: BTCUSDT (Bitcoin/USDT pair)
- Time Interval: 1 day
- Timeframe: 500 intervals

This strategy aims to capture medium to long-term uptrends by entering when shorter-term momentum (50 MA) confirms the longer-term trend 
direction (200 MA). The golden cross is considered one of the most reliable bullish signals in technical analysis."""

FAILURE_RESPONSE = """No specific trading strategy was provided in the prompt.

Since no strategy details were given, I cannot create a meaningful trading strategy from just "hi!".

A trading strategy requires at least entry conditions to be defined. Please provide details such as:
- When to enter a trade (entry conditions)
- When to exit a trade (exit conditions, if any)
- Any technical indicators you'd like to use
- Market conditions or patterns you want to trade on

For example, you could say something like:
- "Buy when RSI is below 30 and sell when RSI is above 70"
- "Enter long when price breaks above 20-day moving average"
- "Buy on dips and sell after 5% profit"

Please provide your trading strategy idea, and I'll help you develop it into a complete backtestable strategy!"""


@pytest.fixture(scope="module")
def strategy_factory() -> StrategyFactory:
    strategies_path = Path(__file__).parent / "strategies"
    return StrategyFactory(strategies_path=strategies_path)


def test_from_description_success(strategy_factory):
    strategy_builder = strategy_factory.from_description(SUCCESS_RESPONSE)

    assert strategy_builder is not None
    assert strategy_builder.name == "Golden Cross Moving Average Crossover (1)"
    assert strategy_builder.slug == "golden_cross_moving_average_crossover_1"


def test_from_description_failure(strategy_factory):
    strategy_builder = strategy_factory.from_description(FAILURE_RESPONSE)

    assert strategy_builder is None


def test_from_filepath(strategy_factory):
    filepath = Path(__file__).parent / "strategies" / "golden_cross_moving_average_crossover_1.py"

    strategy_builder = strategy_factory.from_filepath(filepath)

    assert strategy_builder.filepath == filepath
    assert strategy_builder.name == "Golden Cross Moving Average Crossover 1"
    assert strategy_builder.slug == "golden_cross_moving_average_crossover_1"
    assert strategy_builder.description == "**Strategy Name:**\nGolden Cross Moving Average Crossover 1"
