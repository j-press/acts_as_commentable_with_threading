"""Infrastructure automation prototype (Python)."""

from .agent import AutomationAgent
from .config import load_config

__all__ = ["AutomationAgent", "load_config"]
