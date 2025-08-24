from __future__ import annotations

from constants import serverPackets
from objects import glob
import logging

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # get token data
    userID = userToken.userID

    # Send spectator frames to every spectator
    streamName = f"spect/{userID}"
    glob.streams.broadcast(streamName, serverPackets.spectator_frames(packetData[7:]))
    logger.debug(
        "Broadcasting {}'s frames to {} clients".format(
            userID,
            len(glob.streams.streams[streamName].clients),
        ),
    )
