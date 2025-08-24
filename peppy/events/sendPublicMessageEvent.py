from __future__ import annotations

from helpers import chatHelper as chat
from packets import client


def handle(userToken, packetData):
    # Send public message packet
    packetData = client.sendPublicMessage(packetData)
    chat.sendMessage(
        token=userToken,
        to=packetData["to"],
        message=packetData["message"],
    )
