"""Base agent interface and abstract classes."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, description: str):
        """Initialize agent with name and description."""
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic with given context."""
        raise NotImplementedError

    @abstractmethod
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input context before execution."""
        raise NotImplementedError
