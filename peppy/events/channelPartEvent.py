from __future__ import annotations

from helpers import chatHelper as chat
from packets import client


def handle(userToken, packetData):
    # Channel join packet
    packetData = client.channelPart(packetData)
    chat.partChannel(token=userToken, channel=packetData["channel"])
