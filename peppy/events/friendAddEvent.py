from __future__ import annotations

from common.ripple import userUtils
from constants import clientPackets
import logging

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # Friend add packet
    packetData = clientPackets.addRemoveFriend(packetData)
    userUtils.addFriend(userToken.userID, packetData["friendID"])

    # Console output
    logger.info(
        "{} have added {} to their friends".format(
            userToken.username,
            str(packetData["friendID"]),
        ),
    )
