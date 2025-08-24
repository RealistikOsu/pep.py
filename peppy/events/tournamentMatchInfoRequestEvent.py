from __future__ import annotations

from objects import glob
from packets import client


def handle(userToken, packetData):
    packetData = client.tournamentMatchInfoRequest(packetData)
    matchID = packetData["matchID"]
    if matchID not in glob.matches.matches or not userToken.tournament:
        return
    with glob.matches.matches[matchID] as m:
        userToken.enqueue(m.matchDataCache)
