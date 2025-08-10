from .base import BaseTool


class NewStrategyTool(BaseTool):
    name = "new_strategy"
    description = "Resets the workflow. Use when user wants to start a new strategy from scratch."

    def execute(self, description: str = "") -> str:
        return description and description.strip()

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "The new strategy description. If provided, it will be used to initialize the strategy.",
                    }
                },
                "additionalProperties": False,
            },
        }
