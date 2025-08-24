from __future__ import annotations

from objects import glob
from packets import client


def handle(userToken, packetData):
    # Read token and packet data
    userID = userToken.userID
    packetData = client.matchInvite(packetData)

    # Get match ID and match object
    matchID = userToken.matchID

    # Make sure we are in a match
    if matchID == -1:
        return

    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return

    # Send invite
    with glob.matches.matches[matchID] as match:
        match.invite(userID, packetData["userID"])
