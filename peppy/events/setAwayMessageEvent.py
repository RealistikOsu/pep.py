from __future__ import annotations

import logging

from constants import clientPackets
from constants import serverPackets
from objects import glob

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # get token data
    username = userToken.username

    # Read packet data
    packetData = clientPackets.setAwayMessage(packetData)

    # Set token away message
    userToken.awayMessage = packetData["awayMessage"]

    # Send private message from the bot
    if packetData["awayMessage"] == "":
        fokaMessage = "Your away message has been reset"
    else:
        fokaMessage = f"Your away message is now: {packetData['awayMessage']}"
    userToken.enqueue(
        serverPackets.message_notify(glob.BOT_NAME, username, fokaMessage),
    )
    logger.info(
        "{} has changed their away message to: {}".format(
            username,
            packetData["awayMessage"],
        ),
    )
