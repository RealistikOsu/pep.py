from __future__ import annotations

from common.generalUtils import calc_acc
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
        assert slotID is not None

        # Update the score
        if match.pp_competition:
            slot_mods = match.slots[slotID].mods | match.mods
            passed_objects = (
                data["count300"]
                + data["count100"]
                + data["count50"]
                + data["countMiss"]
            )
            accuracy = calc_acc(
                match.gameMode,
                data["count300"],
                data["count100"],
                data["count50"],
                data["countMiss"],
                data["countKatu"],
                data["countGeki"],
            )
            performance = glob.performance_service.calculate_performance_single(
                beatmap_id=match.beatmapID,
                mode=match.gameMode,
                mods=slot_mods,
                max_combo=data["maxCombo"],
                accuracy=accuracy,
                miss_count=data["countMiss"],
                passed_objects=passed_objects,
            )

            match.updateScore(slotID, int(performance.pp))
            data["totalScore"] = int(performance.pp)
        else:
            match.updateScore(slotID, data["totalScore"])

        match.updateHP(slotID, data["currentHp"])

        # Enqueue frames to who's playing
        glob.streams.broadcast(
            match.playingStreamName,
            serverPackets.match_frames(
                time=data["time"],
                slot_id=slotID,
                count_300=data["count300"],
                count_100=data["count100"],
                count_50=data["count50"],
                count_geki=data["countGeki"],
                count_katu=data["countKatu"],
                count_miss=data["countMiss"],
                total_score=data["totalScore"],
                max_combo=data["maxCombo"],
                current_combo=data["currentCombo"],
                perfect=data["perfect"],
                current_hp=data["currentHp"],
                tag_byte=data["tagByte"],
                using_score_v2=data["usingScoreV2"],
            ),
        )
