from __future__ import annotations

import logging

from common.ripple import userUtils
from packets import client

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # Friend remove packet
    packetData = client.addRemoveFriend(packetData)
    userUtils.removeFriend(userToken.userID, packetData["friendID"])

    # Console output
    logger.info(
        "{} have removed {} from their friends".format(
            userToken.username,
            str(packetData["friendID"]),
        ),
    )
