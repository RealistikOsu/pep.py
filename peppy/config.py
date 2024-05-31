from __future__ import annotations

import os
from dataclasses import dataclass
from json import dump
from json import load
from typing import Any

from logger import log as logger  # TODO: tf.


@dataclass
class Config:
    PORT: int = 5001
    DB_HOST: str = "localhost"
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = "lole"
    DB_DATABASE: str = "rosu"
    DB_WORKERS: int = 4
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    THREADS_COUNT: int = 2
    NEW_RANKED_WEBHOOK: str = ""
    USING_CF: bool = True
    SRV_NAME: str = "RealistikOsu"
    SRV_DOMAIN: str = "ussr.pl"
    SRV_BOT_NAME: str = "RealistikBot"
    SRV_BOT_ID: int = 999
    SRV_MIN_CLIENT_YEAR: int = 2022
    MAPS_DIRECTORY: str = "/home/realistikosu/ussr/.data/maps/"


def read_config_json() -> dict[str, Any]:
    with open("config.json") as f:
        return load(f)


def write_config(config: Config):
    with open("config.json", "w") as f:
        dump(config.__dict__, f, indent=4)


def load_config() -> Config:
    """Loads the config from the file, handling config updates.
    Note:
        Raises `SystemExit` on config update.
    """

    config_dict = {}

    if os.path.exists("config.json"):
        config_dict = read_config_json()

    # Compare config json attributes with config class attributes
    missing_keys = [key for key in Config.__annotations__ if key not in config_dict]

    # Remove extra fields
    for key in tuple(
        config_dict,
    ):
        if key not in Config.__annotations__:
            del config_dict[key]

    # Create config regardless, populating it with missing keys and removing
    # unnecessary keys.
    config = Config(**config_dict)

    if missing_keys:
        logger.info(f"Your config has been updated with {len(missing_keys)} new keys.")
        logger.debug("Missing keys: " + ", ".join(missing_keys))
        write_config(config)
        raise SystemExit(0)

    return config


config = load_config()
