from __future__ import annotations

from objects import glob
from packets import client


def handle(userToken, packetData):
    # Get packet data
    packetData = client.transferHost(packetData)

    # Get match ID and match object
    matchID = userToken.matchID

    # Make sure we are in a match
    if matchID == -1:
        return

    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return

    # Host check
    with glob.matches.matches[matchID] as match:
        if userToken.userID != match.hostUserID:
            return

        # Transfer host
        match.transferHost(packetData["slotID"])
