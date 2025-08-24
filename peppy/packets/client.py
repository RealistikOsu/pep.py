from __future__ import annotations

from . import reader
from . import types
from ..constants import slotStatuses

""" Users listing packets """


def userActionChange(stream):
    return reader.read_packet_data(
        stream,
        [
            ["actionID", types.BYTE],
            ["actionText", types.STRING],
            ["actionMd5", types.STRING],
            ["actionMods", types.UINT32],
            ["gameMode", types.BYTE],
            ["beatmapID", types.SINT32],
        ],
    )


def userStatsRequest(stream):
    return reader.read_packet_data(stream, [["users", types.INT_LIST]])


def userPanelRequest(stream):
    return reader.read_packet_data(stream, [["users", types.INT_LIST]])


""" Client chat packets """


def sendPublicMessage(stream):
    return reader.read_packet_data(
        stream,
        [
            ["unknown", types.STRING],
            ["message", types.STRING],
            ["to", types.STRING],
        ],
    )


def sendPrivateMessage(stream):
    return reader.read_packet_data(
        stream,
        [
            ["unknown", types.STRING],
            ["message", types.STRING],
            ["to", types.STRING],
            ["unknown2", types.UINT32],
        ],
    )


def setAwayMessage(stream):
    return reader.read_packet_data(
        stream,
        [["unknown", types.STRING], ["awayMessage", types.STRING]],
    )


def channelJoin(stream):
    return reader.read_packet_data(stream, [["channel", types.STRING]])


def channelPart(stream):
    return reader.read_packet_data(stream, [["channel", types.STRING]])


def addRemoveFriend(stream):
    return reader.read_packet_data(stream, [["friendID", types.SINT32]])


""" Spectator packets """


def startSpectating(stream):
    return reader.read_packet_data(stream, [["userID", types.SINT32]])


""" Multiplayer packets """


def matchSettings(stream):
    # Data to return, will be merged later
    data = []

    # Some settings
    struct = [
        ["matchID", types.UINT16],
        ["inProgress", types.BYTE],
        ["unknown", types.BYTE],
        ["mods", types.UINT32],
        ["matchName", types.STRING],
        ["matchPassword", types.STRING],
        ["beatmapName", types.STRING],
        ["beatmapID", types.UINT32],
        ["beatmapMD5", types.STRING],
    ]

    # Slot statuses (not used)
    for i in range(0, 16):
        struct.append([f"slot{str(i)}Status", types.BYTE])

    # Slot statuses (not used)
    for i in range(0, 16):
        struct.append([f"slot{str(i)}Team", types.BYTE])

    # Read first part
    slotData = reader.read_packet_data(stream, struct)

    # Skip userIDs because fuck
    for i in range(0, 16):
        s = slotData[f"slot{str(i)}Status"]
        if s & (4 | 8 | 16 | 32 | 64) > 0:
            struct.append([f"slot{str(i)}UserId", types.SINT32])

    # Other settings
    struct.extend(
        [
            ["hostUserID", types.SINT32],
            ["gameMode", types.BYTE],
            ["scoringType", types.BYTE],
            ["teamType", types.BYTE],
            ["freeMods", types.BYTE],
        ],
    )

    # Results goes here
    result = reader.read_packet_data(stream, struct)
    return result


def createMatch(stream):
    return matchSettings(stream)


def changeMatchSettings(stream):
    return matchSettings(stream)


def changeSlot(stream):
    return reader.read_packet_data(stream, [["slotID", types.UINT32]])


def joinMatch(stream):
    return reader.read_packet_data(
        stream,
        [["matchID", types.UINT32], ["password", types.STRING]],
    )


def changeMods(stream):
    return reader.read_packet_data(stream, [["mods", types.UINT32]])


def lockSlot(stream):
    return reader.read_packet_data(stream, [["slotID", types.UINT32]])


def transferHost(stream):
    return reader.read_packet_data(stream, [["slotID", types.UINT32]])


def matchInvite(stream):
    return reader.read_packet_data(stream, [["userID", types.UINT32]])


def match_frames(stream):
    return reader.read_packet_data(
        stream,
        [
            ["time", types.SINT32],
            ["id", types.BYTE],
            ["count300", types.UINT16],
            ["count100", types.UINT16],
            ["count50", types.UINT16],
            ["countGeki", types.UINT16],
            ["countKatu", types.UINT16],
            ["countMiss", types.UINT16],
            ["totalScore", types.SINT32],
            ["maxCombo", types.UINT16],
            ["currentCombo", types.UINT16],
            ["perfect", types.BYTE],
            ["currentHp", types.BYTE],
            ["tagByte", types.BYTE],
            ["usingScoreV2", types.BYTE],
        ],
    )


def tournamentMatchInfoRequest(stream):
    return reader.read_packet_data(stream, [["matchID", types.UINT32]])


def tournamentJoinMatchChannel(stream):
    return reader.read_packet_data(stream, [["matchID", types.UINT32]])


def tournamentLeaveMatchChannel(stream):
    return reader.read_packet_data(stream, [["matchID", types.UINT32]])
