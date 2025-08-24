from __future__ import annotations

import logging

from constants import clientPackets
from constants import serverPackets

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # Read userIDs list
    packetData = clientPackets.userStatsRequest(packetData)

    # Process lists with length <= 32
    if len(packetData) > 32:
        logger.warning("Received userStatsRequest with length > 32")
        return

    for i in packetData["users"]:
        logger.debug("Sending stats for user", extra={"user_id": i})

        # Skip our stats
        if i == userToken.userID:
            continue

        # Enqueue stats packets relative to this user
        userToken.enqueue(serverPackets.user_stats(i))
