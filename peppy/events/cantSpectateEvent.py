from __future__ import annotations

import logging

from constants import exceptions
from objects import glob
from packets import server

logger = logging.getLogger(__name__)


def handle(userToken, _):
    try:
        # We don't have the beatmap, we can't spectate
        if userToken.spectating not in glob.tokens.tokens:
            raise exceptions.tokenNotFoundException()

        # Send the packet to host
        glob.tokens.tokens[userToken.spectating].enqueue(
            server.spectator_song_missing(userToken.userID),
        )
    except exceptions.tokenNotFoundException:
        # Stop spectating if token not found
        logger.warning("Spectator can't spectate: token not found")
        userToken.stopSpectating()
