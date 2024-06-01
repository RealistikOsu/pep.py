from __future__ import annotations

from events import matchBeatmapEvent


def handle(userToken, packetData):
    matchBeatmapEvent.handle(userToken, packetData, False)
