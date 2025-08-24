from __future__ import annotations

import logging

from helpers import chatHelper as chat

logger = logging.getLogger(__name__)


def handle(userToken, _):
    # Get usertoken data
    username = userToken.username

    # Remove user from users in lobby
    userToken.leaveStream("lobby")

    # Part lobby channel
    # Done automatically by the client
    chat.partChannel(channel="#lobby", token=userToken, kick=True)

    # Console output
    logger.info("User left multiplayer lobby", extra={"username": username})
