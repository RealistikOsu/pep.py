from __future__ import annotations

import logging

from objects import glob
from packets import server

logger = logging.getLogger(__name__)


def handle(userToken, _):
    # Get userToken data
    username = userToken.username

    # Add user to users in lobby
    userToken.joinStream("lobby")

    # Send matches data
    for key, _ in glob.matches.matches.items():
        userToken.enqueue(server.match_create(key))

    # Console output
    logger.info("User joined multiplayer lobby", extra={"username": username})
