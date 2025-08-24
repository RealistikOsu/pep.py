from __future__ import annotations

from packets import server


def handle(userToken, packetData):
    # Update cache and send new stats
    userToken.updateCachedStats()
    userToken.enqueue(server.user_stats(userToken.userID))
