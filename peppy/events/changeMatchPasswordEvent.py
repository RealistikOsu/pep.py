from __future__ import annotations

from objects import glob
from packets import client


def handle(userToken, packetData):
    # Read packet data. Same structure as changeMatchSettings
    packetData = client.changeMatchSettings(packetData)

    # Make sure the match exists
    matchID = userToken.matchID
    if matchID not in glob.matches.matches:
        return

    with glob.matches.matches[matchID] as match:
        # Host check
        if userToken.userID != match.hostUserID:
            return

        # Update match password
        match.changePassword(packetData["matchPassword"])
