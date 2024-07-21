from __future__ import annotations

from constants import clientPackets
from constants import serverPackets
from common.generalUtils import calc_acc
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
        assert slotID is not None

        # Update the score
        if match.pp_competition:
            slot_mods = match.slots[slotID].mods | match.mods
            passed_objects = data["count300"] + data["count100"] + data["count50"] + data["countMiss"]
            accuracy = calc_acc(
                match.gameMode,
                data["count300"],
                data["count100"],
                data["count50"],
                data["countMiss"],
                data["countKatu"],
                data["countGeki"],
            )
            performance = glob.performance_service.calculate_performance(
                beatmap_id=match.beatmapID,
                mode=match.gameMode,
                mods=slot_mods,
                max_combo=data["maxCombo"],
                accuracy=accuracy,
                miss_count=data["countMiss"],
                passed_objects=passed_objects,
            )

            match.updateScore(slotID, int(performance.pp))
        else:
            match.updateScore(slotID, data["totalScore"])
        
        match.updateHP(slotID, data["currentHp"])

        # Enqueue frames to who's playing
        glob.streams.broadcast(
            match.playingStreamName,
            serverPackets.match_frames(slotID, packetData),
        )
