"""Deterministic checks for common AI-writing tells."""

from .config import DetectorConfig, load_config
from .detector import lint_batch, lint_text

__all__ = ["DetectorConfig", "lint_batch", "lint_text", "load_config"]
__version__ = "1.0.0"
