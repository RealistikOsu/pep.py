from __future__ import annotations

from helpers import chatHelper as chat
from objects import glob
from packets import client


def handle(userToken, packetData):
    packetData = client.tournamentJoinMatchChannel(packetData)
    matchID = packetData["matchID"]
    if matchID not in glob.matches.matches or not userToken.tournament:
        return
    userToken.matchID = matchID
    chat.joinChannel(token=userToken, channel=f"#multi_{matchID}", force=True)
