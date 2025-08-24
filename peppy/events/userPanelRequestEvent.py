from __future__ import annotations

from constants import clientPackets
from constants import serverPackets
import logging

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # Read userIDs list
    packetData = clientPackets.userPanelRequest(packetData)

    # Process lists with length <= 32
    if len(packetData) > 256:
        logger.warning("Received userPanelRequest with length > 256")
        return

    for i in packetData["users"]:
        # Enqueue userpanel packets relative to this user
        logger.debug("Sending panel for user {i}")
        userToken.enqueue(serverPackets.user_presence(i))
