from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
"""FokaBot related functions"""
from __future__ import annotations

import time
import traceback
from importlib import reload

import settings
from common.constants import actions
from common.ripple import users
from constants import fokabotCommands
from packets import server
from objects import glob


def connect():
    """
    Connect FokaBot to Bancho

    :return:
    """
    glob.BOT_NAME = users.get_username(settings.PS_BOT_USER_ID)
    token = glob.tokens.addToken(settings.PS_BOT_USER_ID)
    token.actionID = actions.WATCHING
    token.actionText = f"over {settings.PS_NAME}!"
    token.pp = 69
    token.accuracy = 0.69
    token.playcount = 69
    token.totalScore = 1337
    token.timeOffset = 0
    token.country = 2  # this is retared, fuck it im keeping it as europe, couldnt find the uk as its ordered stupidly
    token.location = (39.01955903386848, 125.75276158057767)  # Pyongyang red square
    glob.streams.broadcast("main", server.user_presence(settings.PS_BOT_USER_ID))
    glob.streams.broadcast("main", server.user_stats(settings.PS_BOT_USER_ID))


def reload_commands():
    """Reloads the Fokabot commands module."""
    reload(fokabotCommands)


def disconnect():
    """
    Disconnect FokaBot from Bancho

    :return:
    """
    glob.tokens.deleteToken(glob.tokens.getTokenFromUserID(settings.PS_BOT_USER_ID))


def fokabotResponse(fro, chan, message):
    """
    Check if a message has triggered FokaBot

    :param fro: sender username
    :param chan: channel name (or receiver username)
    :param message: chat mesage
    :return: FokaBot's response or False if no response
    """
    DEFAULT_RESPONSE = (
        f"Hello I'm {glob.BOT_NAME}! The server's official bot to assist you, "
        "if you want to know what I can do just type !help"
    )
    start = time.perf_counter_ns()

    # This check is neccessary with ripple.
    if fro == glob.BOT_NAME:
        return False

    user = glob.tokens.getTokenFromUsername(fro)
    assert len(message) > 0

    if message[0] not in ("!", "\x01") and not chan.startswith("#"):
        return DEFAULT_RESPONSE

    for regex, cmd in fokabotCommands.commands.items():
        if not regex.match(message):
            continue

        args = message.removeprefix(cmd.trigger).strip().split(" ")
        if cmd.privileges and not user.privileges & cmd.privileges:
            return False

        if cmd.syntax and not len(args) >= len(cmd.syntax.split(" ")):
            return f"Wrong syntax: {cmd.trigger} {cmd.syntax}"

        try:
            # Now we're executing command callback.
            if not (resp := cmd.callback(fro, chan, args)):
                return False

            resp = [resp]
            if user.admin:  # I'm addicted to benchmarking lmao -len4ee
                resp.append(f"Elapsed: {(time.perf_counter_ns() - start) / 1e6:.2f}ms")

            return " | ".join(resp)
        except Exception:
            # If exception happens, handle it well.
            tb = traceback.format_exc()
            logger.error(
                f"There was an issue while running '{cmd.trigger}' command. \nTraceback: {tb}",
            )
            resp = [
                f"There was issue while processing your command, please report this to {settings.PS_NAME} developer!",
            ]
            # Debugging for staff
            if user.admin:
                resp.append(tb)
                resp.append(f"Elasped: {(time.perf_counter_ns() - start) / 1e6:.2f}ms")
            return "\n".join(resp)

    return False
