from __future__ import annotations

from objects import glob
from packets import client


def handle(userToken, packetData):
    # Get usertoken data
    userID = userToken.userID

    # Read packet data
    packetData = client.changeSlot(packetData)

    with glob.matches.matches[userToken.matchID] as match:
        # Change slot
        match.userChangeSlot(userID, packetData["slotID"])
