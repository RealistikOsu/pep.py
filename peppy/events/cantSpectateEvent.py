from __future__ import annotations

from constants import exceptions
from constants import serverPackets
from logger import log
from objects import glob


def handle(userToken, _):
    try:
        # We don't have the beatmap, we can't spectate
        if userToken.spectating not in glob.tokens.tokens:
            raise exceptions.tokenNotFoundException()

        # Send the packet to host
        glob.tokens.tokens[userToken.spectating].enqueue(
            serverPackets.spectator_song_missing(userToken.userID),
        )
    except exceptions.tokenNotFoundException:
        # Stop spectating if token not found
        log.warning("Spectator can't spectate: token not found")
        userToken.stopSpectating()
