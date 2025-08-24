from __future__ import annotations

from helpers import chatHelper as chat
from objects import glob
from packets import client


def handle(userToken, packetData):
    packetData = client.tournamentLeaveMatchChannel(packetData)
    matchID = packetData["matchID"]
    if matchID not in glob.matches.matches or not userToken.tournament:
        return
    chat.partChannel(token=userToken, channel=f"#multi_{matchID}", force=True)
    userToken.matchID = 0
