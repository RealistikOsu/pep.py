from __future__ import annotations

import json
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from common.ripple import userUtils
from config import config
from constants import exceptions
from constants import serverPackets
from events import logoutEvent
from logger import log
from objects import fokabot
from objects import glob

if TYPE_CHECKING:
    from objects.osuToken import UserToken


def joinChannel(
    userID: Optional[int] = None,
    channel: str = "",
    token: Optional[UserToken] = None,
    force: bool = False,
):
    """
    Join a channel

    :param userID: user ID of the user that joins the channel. Optional. token can be used instead.
    :param token: user token object of user that joins the channel. Optional. userID can be used instead.
    :param channel: channel name
    :param toIRC: if True, send this channel join event to IRC. Must be true if joining from bancho. Default: True
    :param force: whether to allow game clients to join #spect_ and #multi_ channels
    :return: 0 if joined or other IRC code in case of error. Needed only on IRC-side
    """
    try:
        # Get token if not defined
        if token is None:
            token = glob.tokens.getTokenFromUserID(userID)
            # Make sure the token exists
            if token is None:
                raise exceptions.userNotFoundException

        # Normal channel, do check stuff
        # Make sure the channel exists
        if channel not in glob.channels.channels:
            raise exceptions.channelUnknownException()

        # Make sure a game client is not trying to join a #multi_ or #spect_ channel manually
        channelObject = glob.channels.channels[channel]
        if channelObject.isSpecial and not token.irc and not force:
            raise exceptions.channelUnknownException()

        # Add the channel to our joined channel
        token.joinChannel(channelObject)

        # Console output
        log.info(f"{token.username} joined channel {channel}")

        # IRC code return
        return 0
    except exceptions.channelNoPermissionsException:
        log.warning(
            "{} attempted to join channel {}, but they have no read permissions".format(
                token.username,
                channel,
            ),
        )
        return 403
    except exceptions.channelUnknownException:
        log.warning(
            "{} attempted to join an unknown channel ({})".format(
                token.username,
                channel,
            ),
        )
        return 403
    except exceptions.userAlreadyInChannelException:
        log.warning(f"User {token.username} already in channel {channel}")
        return 403
    except exceptions.userNotFoundException:
        log.warning("User not connected to IRC/Bancho")
        return 403  # idk


def partChannel(
    userID: Optional[int] = None,
    channel: str = "",
    token: Optional[UserToken] = None,
    kick: bool = False,
    force: bool = False,
) -> None:
    """
    Part a channel

    :param userID: user ID of the user that parts the channel. Optional. token can be used instead.
    :param token: user token object of user that parts the channel. Optional. userID can be used instead.
    :param channel: channel name
    :param toIRC: if True, send this channel join event to IRC. Must be true if joining from bancho. Optional. Default: True
    :param kick: if True, channel tab will be closed on client. Used when leaving lobby. Optional. Default: False
    :param force: whether to allow game clients to part #spect_ and #multi_ channels
    :return: 0 if joined or other IRC code in case of error. Needed only on IRC-side
    """
    try:
        # Make sure the client is not drunk and sends partChannel when closing a PM tab
        if not channel.startswith("#"):
            return

        # Get token if not defined
        if token is None:
            token = glob.tokens.getTokenFromUserID(userID)
            # Make sure the token exists
            if token is None:
                raise exceptions.userNotFoundException()

        # Determine internal/client name if needed
        # (toclient is used clientwise for #multiplayer and #spectator channels)
        channelClient = channel
        if channel == "#spectator":
            if token.spectating is None:
                s = userID
            else:
                s = token.spectatingUserID
            channel = f"#spect_{s}"
        elif channel == "#multiplayer":
            channel = f"#multi_{token.matchID}"
        elif channel.startswith("#spect_"):
            channelClient = "#spectator"
        elif channel.startswith("#multi_"):
            channelClient = "#multiplayer"

        # Make sure the channel exists
        if channel not in glob.channels.channels:
            raise exceptions.channelUnknownException()

        # Make sure a game client is not trying to join a #multi_ or #spect_ channel manually
        channelObject = glob.channels.channels[channel]
        if channelObject.isSpecial and not token.irc and not force:
            raise exceptions.channelUnknownException()

        # Make sure the user is in the channel
        if channel not in token.joinedChannels:
            raise exceptions.userNotInChannelException()

        # Part channel (token-side and channel-side)
        token.partChannel(channelObject)

        # Delete temporary channel if everyone left
        if f"chat/{channelObject.name}" in glob.streams.streams:
            if (
                channelObject.temp
                and len(
                    glob.streams.streams[f"chat/{channelObject.name}"].clients,
                )
                - 1
                == 0
            ):
                glob.channels.removeChannel(channelObject.name)

        # Force close tab if needed
        # NOTE: Maybe always needed, will check later
        if kick:
            token.enqueue(serverPackets.channel_kicked(channelClient))

        # Console output
        log.info(
            f"{token.username} parted channel {channel} ({channelClient})",
        )

    except exceptions.channelUnknownException:
        log.warning(
            "{} attempted to part an unknown channel ({})".format(
                token.username,
                channel,
            ),
        )
    except exceptions.userNotInChannelException:
        log.warning(
            "{} attempted to part {}, but he's not in that channel".format(
                token.username,
                channel,
            ),
        )
    except exceptions.userNotFoundException:
        log.warning("User not connected to IRC/Bancho")


def log_message_db(fro: UserToken, to_id: Union[int, str], content: str) -> None:
    """Logs the message to the database."""

    if isinstance(to_id, str):
        # Channel Message.
        glob.db.execute(
            "INSERT INTO chat_chan_logs (user_id, target_chan, content) VALUES (%s,%s,%s)",
            (fro.userID, to_id, content),
        )
    else:
        glob.db.execute(
            "INSERT INTO chat_logs (user_id, target_id, content) VALUES (%s,%s,%s)",
            (fro.userID, to_id, content),
        )

    redis_notify_new_msg(fro.userID, to_id, content)


def redis_notify_new_msg(fro: int, to: Union[int, str], content: str) -> None:
    """Notifies the api of a new message."""

    glob.redis.publish(
        "rosu:new_message_notify",
        json.dumps(
            {
                "user_id": fro,
                "target": to,
                "content": content,
            },
        ),
    )


def sendMessage(fro="", to="", message="", token=None, toIRC=True):
    """
    Send a message to osu!bancho and IRC server

    :param fro: sender username. Optional. token can be used instead
    :param to: receiver channel (if starts with #) or username
    :param message: text of the message
    :param token: sender token object. Optional. fro can be used instead
    :param toIRC: if True, send the message to IRC. If False, send it to Bancho only. Default: True
    :return: 0 if joined or other IRC code in case of error. Needed only on IRC-side
    """
    try:
        # tokenString = ""
        # Get token object if not passed
        if token is None:
            token = glob.tokens.getTokenFromUsername(fro)
            if token is None:
                raise exceptions.userNotFoundException()
        else:
            # token object alredy passed, get its string and its username (fro)
            fro = token.username
            # tokenString = token.token

        # Make sure this is not a tournament client
        # if token.tournament:
        #     raise exceptions.userTournamentException()

        # Make sure the user is not in restricted mode
        if token.restricted:
            raise exceptions.userRestrictedException()

        # Make sure the user is not silenced
        if token.silenced:
            raise exceptions.userSilencedException()

        # Redirect !report to the bot
        if message.startswith("!report"):
            to = glob.BOT_NAME

        # Determine internal name if needed
        # (toclient is used clientwise for #multiplayer and #spectator channels)
        toClient = to
        if to == "#spectator":
            if token.spectating is None:
                s = token.userID
            else:
                s = token.spectatingUserID
            to = f"#spect_{s}"
        elif to == "#multiplayer":
            to = f"#multi_{token.matchID}"
        elif to.startswith("#spect_"):
            toClient = "#spectator"
        elif to.startswith("#multi_"):
            toClient = "#multiplayer"

        # Make sure the message is valid
        if not message.strip():
            raise exceptions.invalidArgumentsException()

        # Truncate message if > 2048 characters
        message = message[:2045] + "..." if len(message) > 2048 else message

        # Build packet bytes
        packet = serverPackets.message_notify(token.username, toClient, message)

        # Send the message
        isChannel = to.startswith("#")
        if isChannel:
            # CHANNEL
            # Make sure the channel exists
            if to not in glob.channels.channels:
                raise exceptions.channelUnknownException()

            # Make sure the channel is not in moderated mode
            if glob.channels.channels[to].moderated and not token.admin:
                raise exceptions.channelModeratedException()

            # Make sure we are in the channel
            if to not in token.joinedChannels:
                # I'm too lazy to put and test the correct IRC error code here...
                # but IRC is not strict at all so who cares
                raise exceptions.channelNoPermissionsException()

            # Make sure we have write permissions
            if not glob.channels.channels[to].publicWrite and not token.admin:
                raise exceptions.channelNoPermissionsException()

            # Add message in buffer
            token.addMessageInBuffer(to, message)

            # Everything seems fine, build recipients list and send packet
            glob.streams.broadcast(f"chat/{to}", packet, but=[token.token])
            # Log the message to db and api.
            # These channels can overlap and overall are meant to be temporary.
            if toClient not in ("#multiplayer", "#spectator"):
                log_message_db(token, to, message)
        else:
            # USER
            # Make sure recipient user is connected
            recipientToken = glob.tokens.getTokenFromUsername(to)
            if recipientToken is None:
                user_id = userUtils.getID(to)
                if user_id:
                    log_message_db(token, user_id, message)
                raise exceptions.userNotFoundException()

            # Make sure the recipient is not a tournament client
            # if recipientToken.tournament:
            #     raise exceptions.userTournamentException()

            # Make sure the recipient is not restricted or we are the bot
            if recipientToken.restricted and fro.lower() != glob.BOT_NAME.lower():
                raise exceptions.userRestrictedException()

            # TODO: Make sure the recipient has not disabled PMs for non-friends or he's our friend

            # Away check
            if recipientToken.awayCheck(token.userID):
                sendMessage(
                    to,
                    fro,
                    f"\x01ACTION is away: {recipientToken.awayMessage}\x01",
                )

            # Everything seems fine, send packet
            recipientToken.enqueue(packet)
            log_message_db(token, recipientToken.userID, message)

        # Spam protection (ignore the bot)
        if token.userID > config.SRV_BOT_ID or not token.admin:
            token.spamProtection()

        # Some bot message
        if isChannel or to.lower() == glob.BOT_NAME.lower():
            fokaMessage = fokabot.fokabotResponse(token.username, to, message)
            if fokaMessage:
                sendMessage(glob.BOT_NAME, to if isChannel else fro, fokaMessage)

        # File and discord logs (public chat only)
        if to.startswith("#") and not (
            message.startswith("\x01ACTION is playing") and to.startswith("#spect_")
        ):
            log.chat(
                "{fro} @ {to}: {message}".format(
                    fro=token.username,
                    to=to,
                    message=message.encode("utf-8").decode("utf-8"),
                ),
            )
        return 0
    except exceptions.userSilencedException:
        token.enqueue(serverPackets.silence_end_notify(token.getSilenceSecondsLeft()))
        log.warning(f"{token.username} tried to send a message during silence")
        return 404
    except exceptions.channelModeratedException:
        log.warning(
            "{} tried to send a message to a channel that is in moderated mode ({})".format(
                token.username,
                to,
            ),
        )
        return 404
    except exceptions.channelUnknownException:
        log.warning(
            "{} tried to send a message to an unknown channel ({})".format(
                token.username,
                to,
            ),
        )
        return 403
    except exceptions.channelNoPermissionsException:
        log.warning(
            "{} tried to send a message to channel {}, but they have no write permissions".format(
                token.username,
                to,
            ),
        )
        return 404
    except exceptions.userRestrictedException:
        log.warning(
            "{} tried to send a message {}, but the recipient is in restricted mode".format(
                token.username,
                to,
            ),
        )
        return 404
    except exceptions.userTournamentException:
        log.warning(
            "{} tried to send a message {}, but the recipient is a tournament client".format(
                token.username,
                to,
            ),
        )
        return 404
    except exceptions.userNotFoundException:
        log.warning("User not connected to IRC/Bancho")
        return 401
    except exceptions.invalidArgumentsException:
        log.warning(
            f"{token.username} tried to send an invalid message to {to}",
        )
        return 404
