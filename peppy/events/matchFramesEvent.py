from __future__ import annotations

from constants import clientPackets
from constants import serverPackets
from objects import glob


def handle(userToken, packetData):
    # Get usertoken data
    userID = userToken.userID

    # Get match ID and match object
    matchID = userToken.matchID

    # Make sure we are in a match
    if matchID == -1:
        return

    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return

    # Parse the data
    data = clientPackets.match_frames(packetData)

    with glob.matches.matches[matchID] as match:
        # Change slot id in packetData
        slotID = match.getUserSlotID(userID)

        # Update the score
        match.updateScore(slotID, data["totalScore"])
        match.updateHP(slotID, data["currentHp"])

        # Enqueue frames to who's playing
        glob.streams.broadcast(
            match.playingStreamName,
            serverPackets.match_frames(slotID, packetData),
        )
