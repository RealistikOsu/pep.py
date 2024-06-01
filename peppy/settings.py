from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

_BOOLEAN_STRINGS = ("true", "1", "yes")
def _parse_bool(value: str) -> bool:
    return value.strip().lower() in _BOOLEAN_STRINGS


def _parse_int_list(value: str) -> list[int]:
    if not value:
        return []
    
    return [int(i) for i in value.strip().replace(", ", ",").split(",")]


HTTP_PORT = int(os.environ["HTTP_PORT"])
HTTP_ADDRESS = os.environ["HTTP_ADDRESS"]
HTTP_THREAD_COUNT = int(os.environ["HTTP_THREAD_COUNT"])
HTTP_USING_CLOUDFLARE = _parse_bool(os.environ["HTTP_USING_CLOUDFLARE"])

MYSQL_HOST = os.environ["MYSQL_HOST"]
MYSQL_PORT = int(os.environ["MYSQL_PORT"])
MYSQL_USER = os.environ["MYSQL_USER"]
MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
MYSQL_POOL_SIZE = int(os.environ["MYSQL_POOL_SIZE"])

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]
REDIS_DB = int(os.environ["REDIS_DB"])

DISCORD_RANKED_WEBHOOK_URL = os.environ["DISCORD_RANKED_WEBHOOK_URL"]

# TODO: Find a better acronym to call an "osu! private server" than "PS"
PS_NAME = os.environ["PS_NAME"]
PS_DOMAIN = os.environ["PS_DOMAIN"]
PS_BOT_USERNAME = os.environ["PS_BOT_USERNAME"]
PS_BOT_USER_ID = int(os.environ["PS_BOT_USER_ID"])
PS_MINIMUM_CLIENT_YEAR = int(os.environ["PS_MINIMUM_CLIENT_YEAR"])
PS_ENABLE_PY_COMMAND = _parse_bool(os.environ["PS_ENABLE_PY_COMMAND"])
PS_PY_COMMAND_WHITELIST = _parse_int_list(os.environ["PS_PY_COMMAND_WHITELIST"])

DATA_BEATMAP_DIRECTORY = os.environ["DATA_BEATMAP_DIRECTORY"]
DATA_GEOLOCATION_PATH = os.environ["DATA_GEOLOCATION_PATH"]
DATA_BIBLE_PATH = os.environ["DATA_BIBLE_PATH"]
