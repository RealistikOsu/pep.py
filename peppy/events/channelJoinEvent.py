from __future__ import annotations

from helpers import chatHelper as chat
from packets import client


def handle(userToken, packetData):
    # Channel join packet
    packetData = client.channelJoin(packetData)
    chat.joinChannel(token=userToken, channel=packetData["channel"])
