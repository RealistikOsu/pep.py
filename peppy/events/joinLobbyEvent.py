from __future__ import annotations

from constants import serverPackets
from objects import glob
import logging

logger = logging.getLogger(__name__)


def handle(userToken, _):
    # Get userToken data
    username = userToken.username

    # Add user to users in lobby
    userToken.joinStream("lobby")

    # Send matches data
    for key, _ in glob.matches.matches.items():
        userToken.enqueue(serverPackets.match_create(key))

    # Console output
    logger.info("{username} has joined multiplayer lobby")
