from __future__ import annotations

import logging.config
import sys
from pathlib import Path

import yaml

# Debug mode detection
DEBUG = "debug" in sys.argv


def configure_logging() -> None:
    """Configure logging from logging.yaml file."""
    config_file = Path("logging.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Logging configuration file not found: {config_file}")

    with open(config_file) as f:
        config = yaml.safe_load(f)

    logging.config.dictConfig(config)


# Export for backward compatibility during transition
__all__ = (
    "configure_logging",
    "DEBUG",
)
