"""Global objects and variables"""
from __future__ import annotations

import time
from multiprocessing.pool import ThreadPool
from typing import TYPE_CHECKING

from redis import Redis

from collection.channels import ChannelList
from collection.matches import MatchList
from collection.streams import StreamList
from collection.tokens import TokenList
from common.db.dbConnector import DatabasePool
from config import config
from objects.banchoConfig import banchoConfig

if TYPE_CHECKING:
    from helpers.status_helper import StatusManager

# Consts.
BOT_NAME = config.SRV_BOT_NAME

__version__ = "3.1.0"

application = None
db: DatabasePool
redis: Redis
banchoConf: banchoConfig
namespace = {}
streams = StreamList()
tokens = TokenList()
channels = ChannelList()
matches = MatchList()
cached_passwords: dict[str, str] = {}
chatFilters = None
pool: ThreadPool
busyThreads = 0

debug = False
restarting = False

startTime = int(time.time())
user_statuses: StatusManager
