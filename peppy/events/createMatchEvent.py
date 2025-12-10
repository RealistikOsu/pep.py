from __future__ import annotations

from constants import clientPackets
from constants import exceptions
from constants import serverPackets
from logger import log
from objects import glob
from helpers import chatHelper as chat
from settings import settings


def handle(userToken, packetData):
    try:
        # get usertoken data
        userID = userToken.userID

        # Read packet data
        packetData = clientPackets.createMatch(packetData)

        # Make sure the name is valid
        matchName = packetData["matchName"].strip()
        if not matchName:
            raise exceptions.matchCreateError()

        # Create a match object
        # TODO: Player number check
        matchID = glob.matches.createMatch(
            matchName,
            packetData["matchPassword"].strip(),
            packetData["beatmapID"],
            packetData["beatmapName"],
            packetData["beatmapMD5"],
            packetData["gameMode"],
            userID,
        )

        # Make sure the match has been created
        if matchID not in glob.matches.matches:
            raise exceptions.matchCreateError()

        with glob.matches.matches[matchID] as match:
            # Join that match
            userToken.joinMatch(matchID)


            # Multiplayer Room Patch
            for i in range(0, 16):
                if match.slots[i].status != 4:
                    match.slots[i].status = packetData[f"slot{i}Status"]

            # Give host to match creator
            match.setHost(userID)
            match.sendUpdates()
            match.changePassword(packetData["matchPassword"])

            # Send a welcome channel message to the match creator
            chat.sendMessage(
                fro=glob.BOT_NAME,
                to=f"#multi_{match.matchID}",
                message=f"Welcome to {settings.PS_NAME} multiplayer!",
            )
            chat.sendMessage(
                fro=glob.BOT_NAME,
                to=f"#multi_{match.matchID}",
                message=(
                    "By default, RealistikOsu uses PP for multiplayer leaderboards. "
                    "This can be toggled by the host using the !mp pp command."
                ),
            )
    except exceptions.matchCreateError:
        log.error("Error while creating match!")
        userToken.enqueue(serverPackets.match_join_fail())
