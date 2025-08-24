from __future__ import annotations

import logging
import os
import sys
from multiprocessing.pool import ThreadPool
from pathlib import Path

import ddtrace
import redis.exceptions
import settings
import uvicorn
import yaml
from common.db import dbConnector
from common.redis import pubSub
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from helpers import systemHelper as system
from helpers.status_helper import StatusManager
from logger import configure_logging
from logger import DEBUG
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
from routers import create_router


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="pep.py", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


def configure_logging() -> None:
    """Configure logging from logging.yaml file."""
    config_file = Path("logging.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Logging configuration file not found: {config_file}")

    with open(config_file) as f:
        config = yaml.safe_load(f)

    logging.config.dictConfig(config)


def configure_folders() -> None:
    paths: tuple[str, ...] = (".data",)
    created_folders: list[str] = []

    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path, 0o770)
            created_folders.append(path)

    if created_folders:
        logger.info("Created data folders", extra={"folders": created_folders})


def configure_mysql() -> None:
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

    glob.redis.set("peppy:version", glob.__version__)


def configure_bancho_settings() -> None:
    glob.banchoConf = banchoConfig.banchoConfig()


def cleanup_old_sessions() -> None:
    deleted_count = glob.tokens.deleteBanchoSessions()
    if deleted_count:
        logger.info(
            "Old bancho sessions cleaned up",
            extra={"deleted_count": deleted_count},
        )


def configure_thread_pool() -> None:
    glob.pool = ThreadPool(settings.HTTP_THREAD_COUNT)


def configure_fokabot() -> None:
    fokabot.connect()


def configure_channels() -> None:
    channel_count = glob.channels.loadChannels()
    logger.info("Chat channels initialized", extra={"channel_count": channel_count})


def configure_streams() -> None:
    glob.streams.add("main")
    glob.streams.add("lobby")


def configure_background_tasks() -> None:
    glob.tokens.usersTimeoutCheckLoop()
    glob.tokens.spamProtectionResetLoop()
    glob.matches.cleanupLoop()


def configure_user_statuses() -> None:
    status_manager = StatusManager()
    loaded_count = status_manager.load_from_db()
    glob.user_statuses = status_manager

    logger.info("User statuses loaded", extra={"loaded_count": loaded_count})


def configure_pubsub() -> None:
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


def configure_routers(app: FastAPI) -> None:
    router = create_router()
    app.include_router(router)


def main() -> None:
    ddtrace.patch_all()

    configure_logging()

    try:
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

        glob.debug = DEBUG
        if glob.debug:
            logger.warning("Server running in debug mode!")

        logger.info(
            "pep.py server starting",
            extra={
                "address": settings.HTTP_ADDRESS,
                "port": settings.HTTP_PORT,
                "debug_mode": glob.debug,
            },
        )

        configure_pubsub()

        glob.namespace = globals() | {
            mod: __import__(mod) for mod in sys.modules if mod != "glob"
        }

        app = create_app()
        configure_routers(app)

        uvicorn.run(
            app,
            host=settings.HTTP_ADDRESS,
            port=settings.HTTP_PORT,
            log_level="info" if not glob.debug else "debug",
        )
    finally:
        system.dispose()


if __name__ == "__main__":
    main()
