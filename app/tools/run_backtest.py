import os
import subprocess
from pathlib import Path

from .base import BaseTool


class RunBacktestTool(BaseTool):
    name = "run_backtest"
    description = "Runs a backtest on the strategy saved to the file, returns the results of the backtest, or errors."

    def __init__(self, file_path: Path, root_path: Path):
        self._file_path = file_path
        self._root_path = root_path

    def execute(self, plot_to_file=True) -> str:
        env = os.environ.copy()
        if plot_to_file:
            env["CIPHER_PLOT_TO_FILE"] = str(self._file_path.with_suffix(".png"))
        env["CIPHER_CACHE_ROOT"] = str(self._root_path / ".cache")
        env["CIPHER_LOG_LEVEL"] = "ERROR"
        result = subprocess.run(
            [self._root_path / ".venv/bin/python", str(self._file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=env,
        )
        if result.returncode == 0:
            return f"Backtest result:\n{result.stdout.strip()}"
        else:
            return f"Error running backtest:\n{result.stderr.strip()}"

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        }
