from __future__ import annotations

import time
from multiprocessing.pool import ThreadPool
from typing import TYPE_CHECKING

import settings
from adapters import Ip2LocationApi
from adapters import PerformanceServiceApi
from collection.channels import ChannelList
from collection.matches import MatchList
from collection.streams import StreamList
from collection.tokens import TokenList
from common.db.dbConnector import DatabasePool
from objects.banchoConfig import banchoConfig
from redis import Redis

if TYPE_CHECKING:
    from helpers.status_helper import StatusManager

# Consts.
BOT_NAME = settings.PS_BOT_USERNAME

__version__ = "4.0.0"

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
geolocation_api = Ip2LocationApi(
    settings.IP2LOCATION_API_KEY,
    silent_fail=True,
)
performance_service = PerformanceServiceApi(
    settings.PERFORMANCE_SERVICE_URL,
)
