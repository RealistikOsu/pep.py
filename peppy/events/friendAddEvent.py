from __future__ import annotations

import logging

from common.ripple import users
from packets import client

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # Friend add packet
    packetData = client.addRemoveFriend(packetData)
    users.add_friend(userToken.userID, packetData["friendID"])

    # Console output
    logger.info(
        "{} have added {} to their friends".format(
            userToken.username,
            str(packetData["friendID"]),
        ),
    )
