from __future__ import annotations

from helpers import chatHelper as chat
from packets import client


def handle(userToken, packetData):
    # Send private message packet
    packetData = client.sendPrivateMessage(packetData)
    chat.sendMessage(
        token=userToken,
        to=packetData["to"],
        message=packetData["message"],
    )
