import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Strategy:
    description: str
    name: str
    slug: str
    filepath: Path


class StrategyFactory:
    def __init__(self, strategies_path: Path):
        self._strategies_path = strategies_path

    def from_description(self, description: str) -> Optional[Strategy]:
        if "Strategy Name:" not in description:
            return None

        name = description.split("\n")[1].strip()
        slug = re.sub(
            r"[^A-Za-z0-9_]",
            "",
            name.lower().replace(" ", "_").replace("-", "_"),
        )
        if not slug:
            return None

        files_in_folder = set(item.name for item in self._strategies_path.iterdir() if item.is_file())
        filename = f"{slug}.py"

        if filename in files_in_folder:
            for i in range(1, 100):
                _filename = f"{slug}_{i}.py"
                if _filename not in files_in_folder:
                    filename = _filename
                    break
            else:
                raise ValueError("Filename exists.")

        return Strategy(description=description, name=name, slug=slug, filepath=self._strategies_path / filename)

    def from_filepath(self, filepath: Path) -> Strategy:
        filename = filepath.stem
        slug = filename.replace(".py", "")
        name = slug.replace("_", " ").title()
        description = f"**Strategy Name:**\n{name}"

        return Strategy(description=description, name=name, slug=slug, filepath=filepath)
