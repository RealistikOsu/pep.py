from __future__ import annotations

from common.ripple import userUtils
from constants import clientPackets
from logger import log


def handle(userToken, packetData):
    # Friend remove packet
    packetData = clientPackets.addRemoveFriend(packetData)
    userUtils.removeFriend(userToken.userID, packetData["friendID"])

    # Console output
    log.info(
        "{} have removed {} from their friends".format(
            userToken.username,
            str(packetData["friendID"]),
        ),
    )
