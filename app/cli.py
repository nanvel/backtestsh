from pathlib import Path

import typer
from dotenv import load_dotenv


load_dotenv()

app = typer.Typer()


@app.callback()
def callback():
    """backtest.sh"""


@app.command()
def chat(filepath: Path = typer.Argument(None, exists=True)):
    from anthropic import Anthropic
    from rich.console import Console

    from app.agents import PromptExpander, StrategyBacktester
    from app.strategy import StrategyFactory

    root_path = Path(__file__).parent.parent
    strategies_path = root_path / "strategies"

    strategy_factory = StrategyFactory(strategies_path)

    anthropic_client = Anthropic()

    prompt_expander = PromptExpander(
        client=anthropic_client,
        strategy_factory=strategy_factory,
    )
    strategy_backtester = StrategyBacktester(
        client=anthropic_client,
        root_path=root_path,
        framework_docs=(root_path / "app/cipher.md").read_text(),
    )

    console = Console()

    if filepath:
        strategy = strategy_factory.from_filepath(filepath)
    else:
        strategy = prompt_expander(console=console)

    while True:
        prompt = strategy_backtester(console=console, strategy=strategy)
        strategy = prompt_expander(console=console, prompt=prompt)
