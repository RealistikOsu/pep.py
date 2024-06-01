from __future__ import annotations

from helpers import chatHelper as chat
from logger import log


def handle(userToken, _):
    # Get usertoken data
    username = userToken.username

    # Remove user from users in lobby
    userToken.leaveStream("lobby")

    # Part lobby channel
    # Done automatically by the client
    chat.partChannel(channel="#lobby", token=userToken, kick=True)

    # Console output
    log.info(f"{username} has left multiplayer lobby")
