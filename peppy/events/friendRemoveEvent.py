from __future__ import annotations

from common.ripple import userUtils
from constants import clientPackets
import logging

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # Friend remove packet
    packetData = clientPackets.addRemoveFriend(packetData)
    userUtils.removeFriend(userToken.userID, packetData["friendID"])

    # Console output
    logger.info(
        "{} have removed {} from their friends".format(
            userToken.username,
            str(packetData["friendID"]),
        ),
    )
