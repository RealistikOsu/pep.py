from __future__ import annotations

import math
import os
import signal
import sys
import threading
import time

import psutil

from constants import serverPackets
from helpers import consoleHelper
from logger import log
from objects import glob


def dispose():
    """
    Perform some clean up. Called on shutdown.

    :return:
    """
    print("> Disposing server... ")
    log.info(f"Server closing! Bye!")


def runningUnderUnix():
    """
    Get if the server is running under UNIX or NT

    :return: True if running under UNIX, otherwise False
    """
    return True if os.name == "posix" else False


def scheduleShutdown(sendRestartTime, restart, message="", delay=20):
    """
    Schedule a server shutdown/restart

    :param sendRestartTime: time (seconds) to wait before sending server restart packets to every client
    :param restart: if True, server will restart. if False, server will shudown
    :param message: if set, send that message to every client to warn about the shutdown/restart
    :param delay: additional restart delay in seconds. Default: 20
    :return:
    """
    # Console output
    log.info(
        "Pep.py will {} in {} seconds!".format(
            "restart" if restart else "shutdown",
            sendRestartTime + delay,
        ),
    )
    log.info(f"Sending server restart packets in {sendRestartTime} seconds...")

    # Send notification if set
    if message != "":
        glob.streams.broadcast("main", serverPackets.notification(message))

    # Schedule server restart packet
    threading.Timer(
        sendRestartTime,
        glob.streams.broadcast,
        ["main", serverPackets.server_restart(delay * 2 * 1000)],
    ).start()
    glob.restarting = True

    # Restart/shutdown
    if restart:
        action = restartServer
    else:
        action = shutdownServer

    # Schedule actual server shutdown/restart some seconds after server restart packet, so everyone gets it
    threading.Timer(sendRestartTime + delay, action).start()


def restartServer():
    """
    Restart pep.py

    :return:
    """
    log.info("Restarting pep.py...")
    dispose()
    os.execv(sys.executable, [sys.executable] + sys.argv)


def shutdownServer():
    """
    Shutdown pep.py

    :return:
    """
    log.info("Shutting down pep.py...")
    dispose()
    sig = signal.SIGKILL if runningUnderUnix() else signal.CTRL_C_EVENT
    os.kill(os.getpid(), sig)


def getSystemInfo():
    """
    Get a dictionary with some system/server info

    :return: ["unix", "connectedUsers", "webServer", "cpuUsage", "totalMemory", "usedMemory", "loadAverage"]
    """
    data = {
        "unix": runningUnderUnix(),
        "connectedUsers": len(glob.tokens.tokens),
        "matches": len(glob.matches.matches),
    }

    # General stats
    delta = time.time() - glob.startTime
    days = math.floor(delta / 86400)
    delta -= days * 86400

    hours = math.floor(delta / 3600)
    delta -= hours * 3600

    minutes = math.floor(delta / 60)
    delta -= minutes * 60

    seconds = math.floor(delta)

    data["uptime"] = f"{days}d {hours}h {minutes}m {seconds}s"
    data["cpuUsage"] = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    data["totalMemory"] = f"{memory.total / 1074000000:.2f}"
    data["usedMemory"] = f"{memory.active / 1074000000:.2f}"

    # Unix only stats
    if data["unix"]:
        data["loadAverage"] = os.getloadavg()
    else:
        data["loadAverage"] = (0, 0, 0)

    return data
