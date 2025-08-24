from __future__ import annotations

import json
import logging
import time

from helpers import chatHelper as chat
from objects import glob
from packets import server

logger = logging.getLogger(__name__)


def handle(userToken, _=None, deleteToken=True):
    # get usertoken data
    userID = userToken.userID
    username = userToken.username
    requestToken = userToken.token

    # Big client meme here. If someone logs out and logs in right after,
    # the old logout packet will still be in the queue and will be sent to
    # the server, so we accept logout packets sent at least 5 seconds after login
    # if the user logs out before 5 seconds, he will be disconnected later with timeout check
    if int(time.time() - userToken.loginTime) >= 5 or userToken.irc:
        # Stop spectating
        userToken.stopSpectating()

        # Part matches
        userToken.leaveMatch()

        # Part all joined channels
        for i in userToken.joinedChannels:
            chat.partChannel(token=userToken, channel=i)

        # Leave all joined streams
        userToken.leaveAllStreams()

        # Enqueue our disconnection to everyone else
        glob.streams.broadcast("main", server.logout_notify(userID))

        # Delete token
        if deleteToken:
            glob.tokens.deleteToken(requestToken)
        else:
            userToken.kicked = True

        # glob.db.execute("UPDATE users_stats SET current_status = 'Offline' WHERE id = %s", [userID])
        # Change username if needed
        newUsername = glob.redis.get(f"ripple:change_username_pending:{userID}")
        if newUsername is not None:
            logger.debug("Sending username change request", extra={"user_id": userID})
            glob.redis.publish(
                "peppy:change_username",
                json.dumps(
                    {"userID": userID, "newUsername": newUsername.decode("utf-8")},
                ),
            )

        # Console output
        logger.info(
            "User disconnected",
            extra={"username": username, "reason": "logout"},
        )
