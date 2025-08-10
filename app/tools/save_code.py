import subprocess
from pathlib import Path

from .base import BaseTool


class SaveCodeTool(BaseTool):
    name = "save_code"
    description = "The action follows by the code to be saved. Returns SAVED. Saves the strategy code to the file."

    def __init__(self, file_path: Path, root_path: Path):
        self._file_path = file_path
        self._root_path = root_path

    def execute(self, content: str) -> str:
        with open(self._file_path, "w", encoding="utf-8") as file:
            file.write(content)
        subprocess.run(
            [self._root_path / ".venv/bin/isort", str(self._file_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            [self._root_path / ".venv/bin/black", str(self._file_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return "SAVED"

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The code content to be saved to the file.",
                    }
                },
                "required": ["content"],
                "additionalProperties": False,
            },
        }
