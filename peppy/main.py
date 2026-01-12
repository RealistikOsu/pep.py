from __future__ import annotations

import os
import sys
import traceback
from multiprocessing.pool import ThreadPool

#import ddtrace
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
from helpers import consoleHelper
from helpers import systemHelper as system
from helpers.status_helper import StatusManager
from logger import DEBUG
from logger import log
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


def make_app():
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


def main():
    #ddtrace.patch_all()
    try:
        # Server start
        consoleHelper.printServerStartHeader(True)

        # Create data folder if needed
        log.info("Checking folders... ")
        paths = (".data",)
        for i in paths:
            if not os.path.exists(i):
                os.makedirs(i, 0o770)
        log.info("Complete!")

        # Connect to db and redis
        try:
            log.info("Connecting to MySQL database... ")
            glob.db = dbConnector.DatabasePool(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                username=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                initialSize=settings.MYSQL_POOL_SIZE,
            )

            log.info("Connecting to redis... ")
            glob.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
            )
            glob.redis.ping()
        except Exception:
            # Exception while connecting to db
            log.error(
                "Error while connection to database and redis. Please ensure your config and try again.",
            )
            raise

        # Empty redis cache
        try:
            glob.redis.set("ripple:online_users", 0)
            glob.redis.eval(
                "return redis.call('del', unpack(redis.call('keys', ARGV[1])))",
                0,
                "peppy:*",
            )
        except redis.exceptions.ResponseError:
            # Script returns error if there are no keys starting with peppy:*
            pass

        # Save peppy version in redis
        glob.redis.set("peppy:version", glob.__version__)

        # Load bancho_settings
        try:
            log.info("Loading bancho settings from DB... ")
            glob.banchoConf = banchoConfig.banchoConfig()
            log.info("Complete!")
        except:
            log.error(
                "Error while loading bancho_settings. Please make sure the table in DB has all the required rows",
            )
            raise

        # Delete old bancho sessions
        log.info("Deleting cached bancho sessions from DB... ")
        glob.tokens.deleteBanchoSessions()
        log.info("Complete!")

        # Create thread pool
        log.info("Creating thread pool...")
        glob.pool = ThreadPool(settings.HTTP_THREAD_COUNT)
        log.info("Complete!")

        # Start fokabot
        log.info("Connecting RealistikBot...")
        fokabot.connect()
        log.info("Complete!")

        # Initialize chat channels
        log.info("Initializing chat channels... ")
        glob.channels.loadChannels()
        log.info("Complete!")

        # Initialize stremas
        log.info("Creating packets streams... ")
        glob.streams.add("main")
        glob.streams.add("lobby")
        log.info("Complete!")

        # Initialize user timeout check loop
        log.info("Initializing user timeout check loop... ")
        glob.tokens.usersTimeoutCheckLoop()
        log.info("Complete!")

        # Initialize spam protection reset loop
        log.info("Initializing spam protection reset loop... ")
        glob.tokens.spamProtectionResetLoop()
        log.info("Complete!")

        # Initialize multiplayer cleanup loop
        log.info("Initializing multiplayer cleanup loop... ")
        glob.matches.cleanupLoop()
        log.info("Complete!")

        try:
            log.info("Loading user statuses...")
            st_man = StatusManager()
            loaded = st_man.load_from_db()
            glob.user_statuses = st_man
            log.info(f"Loaded {loaded} user statuses!")
        except Exception:
            log.error(
                "Loading user statuses failed with error:\n" + traceback.format_exc(),
            )
            raise

        # Debug mode
        glob.debug = DEBUG
        if glob.debug:
            log.warning("Server running in debug mode!")

        # Make app
        glob.application = make_app()

        # Server start message and console output
        log.info(
            f"pep.py listening for HTTP(s) clients on {settings.HTTP_ADDRESS}:{settings.HTTP_PORT}...",
        )

        # Connect to pubsub channels
        pubSub.listener(
            glob.redis,
            {
                "peppy:disconnect": disconnectHandler.handler(),
                "peppy:reload_settings": lambda x: x == b"reload"
                and glob.banchoConf.reload(),
                "peppy:update_cached_stats": updateStatsHandler.handler(),
                "peppy:silence": updateSilenceHandler.handler(),
                "peppy:ban": banHandler.handler(),
                "peppy:notification": notificationHandler.handler(),
                "peppy:refresh_privs": refreshPrivsHandler.handler(),
                "peppy:bot_msg": bot_msg_handler.handler(),
            },
        ).start()

        # We will initialise namespace for fancy stuff. UPDATE: FUCK OFF WEIRD PYTHON MODULE.
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
