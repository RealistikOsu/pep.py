from __future__ import annotations

import logging
import os
import sys
import traceback
from multiprocessing.pool import ThreadPool

import ddtrace
import redis.exceptions
import settings
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web
from common.db import dbConnector
from common.redis import pubSub
from handlers import api_status
from handlers import apiAerisThing
from handlers import apiOnlineUsersHandler
from handlers import apiServerStatusHandler
from handlers import mainHandler
from helpers import systemHelper as system
from helpers.status_helper import StatusManager
from logger import DEBUG
from logger import configure_logging
from objects import banchoConfig
from objects import fokabot
from objects import glob
from redis_handlers import banHandler
from redis_handlers import bot_msg_handler
from redis_handlers import disconnectHandler
from redis_handlers import notificationHandler
from redis_handlers import refreshPrivsHandler
from redis_handlers import updateSilenceHandler
from redis_handlers import updateStatsHandler

logger = logging.getLogger(__name__)


def make_app() -> tornado.web.Application:
    return tornado.web.Application(
        [
            (r"/", mainHandler.handler),
            (r"/api/v1/onlineUsers", apiOnlineUsersHandler.handler),
            (r"/api/v1/serverStatus", apiServerStatusHandler.handler),
            (r"/api/status/(.*)", api_status.handler),
            (r"/api/v2/status/(.*)", api_status.handler),
            (r"/infos", apiAerisThing.handler),
        ],
    )


def configure_folders() -> None:
    """Create necessary data folders."""
    paths: tuple[str, ...] = (".data",)
    created_folders: list[str] = []

    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path, 0o770)
            created_folders.append(path)

    if created_folders:
        logger.info("Created data folders", extra={"folders": created_folders})


def configure_mysql() -> None:
    """Configure MySQL database connection."""
    logger.info(
        "Connecting to MySQL database",
        extra={
            "host": settings.MYSQL_HOST,
            "port": settings.MYSQL_PORT,
            "database": settings.MYSQL_DATABASE,
            "pool_size": settings.MYSQL_POOL_SIZE,
        },
    )

    glob.db = dbConnector.DatabasePool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        username=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
        initialSize=settings.MYSQL_POOL_SIZE,
    )


def configure_redis() -> None:
    """Configure Redis connection and initialize cache."""
    logger.info(
        "Connecting to Redis",
        extra={
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
        },
    )

    glob.redis = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
    )
    glob.redis.ping()

    # Initialize Redis cache
    glob.redis.set("ripple:online_users", 0)
    try:
        deleted_keys = glob.redis.eval(
            "return redis.call('del', unpack(redis.call('keys', ARGV[1])))",
            0,
            "peppy:*",
        )
        if deleted_keys:
            logger.info("Cleared Redis cache", extra={"deleted_keys": deleted_keys})
    except redis.exceptions.ResponseError:
        # Script returns error if there are no keys starting with peppy:*
        pass

    # Save peppy version in redis
    glob.redis.set("peppy:version", glob.__version__)


def configure_bancho_settings() -> None:
    """Load bancho configuration from database."""
    glob.banchoConf = banchoConfig.banchoConfig()


def cleanup_old_sessions() -> None:
    """Delete old bancho sessions from database."""
    deleted_count = glob.tokens.deleteBanchoSessions()
    if deleted_count:
        logger.info(
            "Old bancho sessions cleaned up", extra={"deleted_count": deleted_count}
        )


def configure_thread_pool() -> None:
    """Create thread pool for HTTP requests."""
    glob.pool = ThreadPool(settings.HTTP_THREAD_COUNT)


def configure_fokabot() -> None:
    """Connect to RealistikBot."""
    fokabot.connect()


def configure_channels() -> None:
    """Initialize chat channels."""
    channel_count = glob.channels.loadChannels()
    logger.info("Chat channels initialized", extra={"channel_count": channel_count})


def configure_streams() -> None:
    """Create packet streams."""
    glob.streams.add("main")
    glob.streams.add("lobby")


def configure_background_tasks() -> None:
    """Initialize background maintenance tasks."""
    # User timeout check loop
    glob.tokens.usersTimeoutCheckLoop()

    # Spam protection reset loop
    glob.tokens.spamProtectionResetLoop()

    # Multiplayer cleanup loop
    glob.matches.cleanupLoop()


def configure_user_statuses() -> None:
    """Load user statuses from database."""
    status_manager = StatusManager()
    loaded_count = status_manager.load_from_db()
    glob.user_statuses = status_manager

    logger.info("User statuses loaded", extra={"loaded_count": loaded_count})


def configure_pubsub() -> None:
    """Configure Redis pubsub channels."""
    pubsub_handlers = {
        "peppy:disconnect": disconnectHandler.handler(),
        "peppy:reload_settings": lambda x: x == b"reload" and glob.banchoConf.reload(),
        "peppy:update_cached_stats": updateStatsHandler.handler(),
        "peppy:silence": updateSilenceHandler.handler(),
        "peppy:ban": banHandler.handler(),
        "peppy:notification": notificationHandler.handler(),
        "peppy:refresh_privs": refreshPrivsHandler.handler(),
        "peppy:bot_msg": bot_msg_handler.handler(),
    }

    pubSub.listener(glob.redis, pubsub_handlers).start()


def main() -> None:
    ddtrace.patch_all()

    # Configure logging
    configure_logging()

    try:
        # Configuration sequence
        configure_folders()
        configure_mysql()
        configure_redis()
        configure_bancho_settings()
        cleanup_old_sessions()
        configure_thread_pool()
        configure_fokabot()
        configure_channels()
        configure_streams()
        configure_background_tasks()
        configure_user_statuses()

        # Debug mode
        glob.debug = DEBUG
        if glob.debug:
            logger.warning("Server running in debug mode!")

        # Make app
        glob.application = make_app()

        # Server start message
        logger.info(
            "pep.py server starting",
            extra={
                "address": settings.HTTP_ADDRESS,
                "port": settings.HTTP_PORT,
                "debug_mode": glob.debug,
            },
        )

        # Configure pubsub
        configure_pubsub()

        # Initialize namespace for fancy stuff
        glob.namespace = globals() | {
            mod: __import__(mod) for mod in sys.modules if mod != "glob"
        }

        # Start tornado
        glob.application.listen(port=settings.HTTP_PORT, address=settings.HTTP_ADDRESS)
        tornado.ioloop.IOLoop.instance().start()
    finally:
        system.dispose()


if __name__ == "__main__":
    main()
