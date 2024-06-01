from __future__ import annotations

from constants import clientPackets
from constants import serverPackets
from logger import log


def handle(userToken, packetData):
    # Read userIDs list
    packetData = clientPackets.userStatsRequest(packetData)

    # Process lists with length <= 32
    if len(packetData) > 32:
        log.warning("Received userStatsRequest with length > 32")
        return

    for i in packetData["users"]:
        log.debug(f"Sending stats for user {i}")

        # Skip our stats
        if i == userToken.userID:
            continue

        # Enqueue stats packets relative to this user
        userToken.enqueue(serverPackets.user_stats(i))
