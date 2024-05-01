""" Contains functions used to write specific server packets to byte streams """
from __future__ import annotations

from common.constants import privileges
from common.ripple import userUtils
from config import config
from constants import dataTypes
from constants import packetIDs
from constants import userRanks
from constants.rosuprivs import BAT
from constants.rosuprivs import DEV_SUPPORTER
from constants.rosuprivs import DEVELOPER
from constants.rosuprivs import MODERATOR
from constants.rosuprivs import OWNER
from helpers import packetHelper
from objects import glob

""" Login errors packets """


def login_failed():
    # return packetHelper.buildPacket(packetIDs.server_userID, ((-1, dataTypes.SINT32)))
    return b"\x05\x00\x00\x04\x00\x00\x00\xff\xff\xff\xff"


def force_update():
    # return packetHelper.buildPacket(packetIDs.server_userID, ((-2, dataTypes.SINT32)))
    return b"\x05\x00\x00\x04\x00\x00\x00\xfe\xff\xff\xff"


def login_banned() -> bytes:
    return login_reply(-1) + notification(
        f"Your account has been banned from {config.SRV_NAME}! "
        "Please contact a member of staff for more information.",
    )


def login_error():
    return b"\x05\x00\x00\x04\x00\x00\x00\xfb\xff\xff\xff"


def login_cheats() -> bytes:
    return login_reply(-1) + notification(
        f"Your account has been restricted from {config.SRV_NAME}! "
        "Please contact a member of staff for more information.",
    )


def verification_required():
    return b"\x05\x00\x00\x04\x00\x00\x00\xf8\xff\xff\xff"


""" Login packets """


def login_reply(user_id: int) -> bytes:
    return packetHelper.buildPacket(
        packetIDs.server_userID,
        ((user_id, dataTypes.SINT32),),
    )


def silence_end_notify(seconds):
    return packetHelper.buildPacket(
        packetIDs.server_silenceEnd,
        ((seconds, dataTypes.UINT32),),
    )


def protocol_version(version=19):
    # This is always 19 so we might as well
    # return packetHelper.buildPacket(packetIDs.server_protocolVersion, ((version, dataTypes.UINT32)))
    return b"K\x00\x00\x04\x00\x00\x00\x13\x00\x00\x00"


def menu_icon(icon):
    return packetHelper.buildPacket(
        packetIDs.server_mainMenuIcon,
        ((icon, dataTypes.STRING),),
    )


def bancho_priv(supporter, GMT, tournamentStaff):
    result = 1
    if supporter:
        result |= userRanks.SUPPORTER
    if GMT:
        result |= userRanks.BAT
    if tournamentStaff:
        result |= userRanks.TOURNAMENT_STAFF
    return packetHelper.buildPacket(
        packetIDs.server_supporterGMT,
        ((result, dataTypes.UINT32),),
    )


def friend_list(userID):
    friends = userUtils.getFriendList(userID)
    return packetHelper.buildPacket(
        packetIDs.server_friendsList,
        ((friends, dataTypes.INT_LIST),),
    )


""" Users packets """


def logout_notify(userID):
    return packetHelper.buildPacket(
        packetIDs.server_userLogout,
        (
            (userID, dataTypes.SINT32),
            (0, dataTypes.BYTE),
        ),
    )


def user_presence(userID, force=False):
    # Connected and restricted check
    userToken = glob.tokens.getTokenFromUserID(userID)
    if userToken is None:
        return b""

    # Get user data
    username = userToken.username
    timezone = 24 + userToken.timeOffset
    country = userToken.country
    gameRank = userToken.gameRank
    latitude = userToken.getLatitude()
    longitude = userToken.getLongitude()

    # Get username colour according to rank
    # Only admins and normal users are currently supported
    userRank = 0
    if username == glob.BOT_NAME:
        userRank |= userRanks.ADMIN
    elif userToken.privileges == OWNER:
        userRank |= userRanks.PEPPY
    elif userToken.privileges in (DEVELOPER, DEV_SUPPORTER):
        userRank |= userRanks.ADMIN
    elif userToken.privileges == MODERATOR:
        userRank |= userRanks.MOD
    elif userToken.privileges & privileges.USER_DONOR:
        userRank |= userRanks.SUPPORTER
    else:
        userRank |= userRanks.NORMAL

    return packetHelper.buildPacket(
        packetIDs.server_userPanel,
        (
            (userID, dataTypes.SINT32),
            (username, dataTypes.STRING),
            (timezone, dataTypes.BYTE),
            (country, dataTypes.BYTE),
            (userRank, dataTypes.BYTE),
            (longitude, dataTypes.FFLOAT),
            (latitude, dataTypes.FFLOAT),
            (gameRank, dataTypes.UINT32),
        ),
    )


def user_stats(userID):
    # Get userID's token from tokens list
    userToken = glob.tokens.getTokenFromUserID(userID)
    if userToken is None:
        return b""

    totalScore = userToken.totalScore
    rankedScore = userToken.rankedScore
    performancePoints = userToken.pp

    # Since performance points are a signed int, send PP as the score (since this mostly
    # will occur in RX and RX players don't care about score).
    if performancePoints >= 32767:
        totalScore = rankedScore = performancePoints
        performancePoints = 0
        

    return packetHelper.buildPacket(
        packetIDs.server_userStats,
        (
            (userID, dataTypes.UINT32),
            (userToken.actionID, dataTypes.BYTE),
            (userToken.actionText, dataTypes.STRING),
            (userToken.actionMd5, dataTypes.STRING),
            (userToken.actionMods, dataTypes.SINT32),
            (userToken.gameMode, dataTypes.BYTE),
            (userToken.beatmapID, dataTypes.SINT32),
            (rankedScore, dataTypes.UINT64),
            (userToken.accuracy, dataTypes.FFLOAT),
            (userToken.playcount, dataTypes.UINT32),
            (totalScore, dataTypes.UINT64),
            (userToken.gameRank, dataTypes.UINT32),
            (performancePoints, dataTypes.SINT16),
        ),
    )


""" Chat packets """


def message_notify(fro: str, to: str, message: str):
    return packetHelper.buildPacket(
        packetIDs.server_sendMessage,
        (
            (fro, dataTypes.STRING),
            (message, dataTypes.STRING),
            (to, dataTypes.STRING),
            (userUtils.getID(fro), dataTypes.SINT32),
        ),
    )


def channel_join_success(chan: str):
    return packetHelper.buildPacket(
        packetIDs.server_channel_join_success,
        ((chan, dataTypes.STRING),),
    )


def channel_info(chan: str):
    if chan not in glob.channels.channels:
        return b""
    channel = glob.channels.channels[chan]
    return packetHelper.buildPacket(
        packetIDs.server_channelInfo,
        (
            (channel.name, dataTypes.STRING),
            (channel.description, dataTypes.STRING),
            (len(glob.streams.streams[f"chat/{chan}"].clients), dataTypes.UINT16),
        ),
    )


def channel_info_end():
    return b"Y\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00"


def channel_kicked(chan):
    return packetHelper.buildPacket(
        packetIDs.server_channelKicked,
        ((chan, dataTypes.STRING),),
    )


def silenced_notify(userID):
    return packetHelper.buildPacket(
        packetIDs.server_userSilenced,
        ((userID, dataTypes.UINT32),),
    )


""" Spectator packets """


def spectator_add(userID):
    return packetHelper.buildPacket(
        packetIDs.server_spectatorJoined,
        ((userID, dataTypes.SINT32),),
    )


def spectator_remove(userID):
    return packetHelper.buildPacket(
        packetIDs.server_spectatorLeft,
        ((userID, dataTypes.SINT32),),
    )


def spectator_frames(data):
    return packetHelper.buildPacket(
        packetIDs.server_spectateFrames,
        ((data, dataTypes.BBYTES),),
    )


def spectator_song_missing(userID):
    return packetHelper.buildPacket(
        packetIDs.server_spectatorCantSpectate,
        ((userID, dataTypes.SINT32),),
    )


def spectator_comrade_joined(user_id: int) -> bytes:
    return packetHelper.buildPacket(
        packetIDs.server_fellowSpectatorJoined,
        ((user_id, dataTypes.SINT32),),
    )


def spectator_comrade_left(userID):
    return packetHelper.buildPacket(
        packetIDs.server_fellowSpectatorLeft,
        ((userID, dataTypes.SINT32),),
    )


""" Multiplayer Packets """


def match_create(matchID):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    matchData = match.getMatchData(censored=True)
    return packetHelper.buildPacket(packetIDs.server_newMatch, matchData)


# TODO: Add match object argument to save some CPU
def match_update(matchID, censored=False):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    return packetHelper.buildPacket(
        packetIDs.server_updateMatch,
        match.getMatchData(censored=censored),
    )


def match_start(matchID: int):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    return packetHelper.buildPacket(packetIDs.server_matchStart, match.getMatchData())


def match_dispose(matchID):
    return packetHelper.buildPacket(
        packetIDs.server_disposeMatch,
        ((matchID, dataTypes.UINT32),),
    )


def match_join_success(matchID):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    data = packetHelper.buildPacket(
        packetIDs.server_matchJoinSuccess,
        match.getMatchData(),
    )
    return data


def match_join_fail():
    return b"%\x00\x00\x00\x00\x00\x00"


def match_change_password(newPassword):
    return packetHelper.buildPacket(
        packetIDs.server_matchChangePassword,
        ((newPassword, dataTypes.STRING),),
    )


def match_all_players_loaded():
    return b"5\x00\x00\x00\x00\x00\x00"


def match_player_skipped(userID):
    return packetHelper.buildPacket(
        packetIDs.server_matchPlayerSkipped,
        ((userID, dataTypes.SINT32),),
    )


def match_all_skipped():
    return b"=\x00\x00\x00\x00\x00\x00"


def match_frames(slotID, data):
    return packetHelper.buildPacket(
        packetIDs.server_matchScoreUpdate,
        (
            (data[7:11], dataTypes.BBYTES),
            (slotID, dataTypes.BYTE),
            (data[12:], dataTypes.BBYTES),
        ),
    )


def match_complete():
    return b":\x00\x00\x00\x00\x00\x00"


def match_player_fail(slotID):
    return packetHelper.buildPacket(
        packetIDs.server_matchPlayerFailed,
        ((slotID, dataTypes.UINT32),),
    )


def match_new_host_notify():
    return b"2\x00\x00\x00\x00\x00\x00"


def match_abort():
    return b"j\x00\x00\x00\x00\x00\x00"


""" Other packets """


def server_switch(address):
    return packetHelper.buildPacket(
        packetIDs.server_switchServer,
        ((address, dataTypes.STRING),),
    )


def notification(message):
    return packetHelper.buildPacket(
        packetIDs.server_notification,
        ((message, dataTypes.STRING),),
    )


def server_restart(msUntilReconnection):
    return packetHelper.buildPacket(
        packetIDs.server_restart,
        ((msUntilReconnection, dataTypes.UINT32),),
    )


def rtx(message):
    return packetHelper.buildPacket(0x69, ((message, dataTypes.STRING),))


def crash():
    # return buildPacket(packetIDs.server_supporterGMT, ((128, dataTypes.UINT32))) + buildPacket(packetIDs.server_ping)
    return b"G\x00\x00\x04\x00\x00\x00\x80\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00"
