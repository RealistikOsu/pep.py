"""Contains functions used to write specific server packets to byte streams"""

from __future__ import annotations

from . import builder
from . import ids
from . import types
from .. import settings
from ..common.constants import privileges
from ..common.ripple import users
from ..constants import userRanks
from ..constants.rosuprivs import BAT
from ..constants.rosuprivs import DEVELOPER
from ..constants.rosuprivs import MODERATOR
from ..constants.rosuprivs import OWNER
from ..objects import glob

""" Login errors packets """


def login_failed():
    # return builder.buildPacket(ids.server_userID, ((-1, types.SINT32)))
    return b"\x05\x00\x00\x04\x00\x00\x00\xff\xff\xff\xff"


def force_update():
    # return builder.buildPacket(ids.server_userID, ((-2, types.SINT32)))
    return b"\x05\x00\x00\x04\x00\x00\x00\xfe\xff\xff\xff"


def login_banned() -> bytes:
    return login_reply(-1) + notification(
        f"Your account has been banned from {settings.PS_NAME}! "
        "Please contact a member of staff for more information.",
    )


def login_error():
    return b"\x05\x00\x00\x04\x00\x00\x00\xfb\xff\xff\xff"


def login_cheats() -> bytes:
    return login_reply(-1) + notification(
        f"Your account has been restricted from {settings.PS_NAME}! "
        "Please contact a member of staff for more information.",
    )


def verification_required():
    return b"\x05\x00\x00\x04\x00\x00\x00\xf8\xff\xff\xff"


""" Login packets """


def login_reply(user_id: int) -> bytes:
    return builder.BinaryWriter().write_i32(user_id).finish(ids.server_userID)


def silence_end_notify(seconds):
    return builder.BinaryWriter().write_u32(seconds).finish(ids.server_silenceEnd)


def protocol_version(version=19):
    # This is always 19 so we might as well
    # return builder.buildPacket(ids.server_protocolVersion, ((version, types.UINT32)))
    return b"K\x00\x00\x04\x00\x00\x00\x13\x00\x00\x00"


def menu_icon(icon):
    return builder.BinaryWriter().write_str(icon).finish(ids.server_mainMenuIcon)


def bancho_priv(supporter, GMT, tournamentStaff):
    result = 1
    if supporter:
        result |= userRanks.SUPPORTER
    if GMT:
        result |= userRanks.BAT
    if tournamentStaff:
        result |= userRanks.TOURNAMENT_STAFF
    return builder.BinaryWriter().write_i32(result).finish(ids.server_supporterGMT)


def friend_list(userID):
    friends = users.get_friend_list(userID)
    return builder.BinaryWriter().write_int_list(friends).finish(ids.server_friendsList)


""" Users packets """


def logout_notify(userID):
    return (
        builder.BinaryWriter()
        .write_i32(userID)
        .write_u8(0)
        .finish(ids.server_userLogout)
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
    elif userToken.privileges == DEVELOPER:
        userRank |= userRanks.ADMIN
    elif userToken.privileges == MODERATOR:
        userRank |= userRanks.MOD
    elif userToken.privileges & privileges.USER_DONOR:
        userRank |= userRanks.SUPPORTER
    else:
        userRank |= userRanks.NORMAL

    return (
        builder.BinaryWriter()
        .write_i32(userID)
        .write_str(username)
        .write_u8(timezone)
        .write_u8(country)
        .write_u8(userRank)
        .write_f32(longitude)
        .write_f32(latitude)
        .write_i32(gameRank)
        .finish(ids.server_userPanel)
    )


def user_stats(userID):
    # Get userID's token from tokens list
    userToken = glob.tokens.getTokenFromUserID(userID)
    if userToken is None:
        return b""

    rankedScore = userToken.rankedScore
    performancePoints = userToken.pp

    # Since performance points are a signed int, send PP as the score (since this mostly
    # will occur in RX and RX players don't care about score).
    if performancePoints >= 32767:
        rankedScore = performancePoints
        performancePoints = 0

    return (
        builder.BinaryWriter()
        .write_i32(userID)
        .write_u8(userToken.actionID)
        .write_str(userToken.actionText)
        .write_str(userToken.actionMd5)
        .write_i32(userToken.actionMods)
        .write_u8(userToken.gameMode)
        .write_i32(userToken.beatmapID)
        .write_i64(rankedScore)
        .write_f32(userToken.accuracy)
        .write_i32(userToken.playcount)
        .write_i64(userToken.totalScore)
        .write_i32(userToken.gameRank)
        .write_i16(performancePoints)
        .finish(ids.server_userStats)
    )


""" Chat packets """


def message_notify(fro: str, to: str, message: str):
    return (
        builder.BinaryWriter()
        .write_str(fro)
        .write_str(message)
        .write_str(to)
        .write_i32(users.get_id(fro))
        .finish(ids.server_sendMessage)
    )


def channel_join_success(chan: str):
    return (
        builder.BinaryWriter().write_str(chan).finish(ids.server_channel_join_success)
    )


def channel_info(chan: str):
    if chan not in glob.channels.channels:
        return b""
    channel = glob.channels.channels[chan]
    return (
        builder.BinaryWriter()
        .write_str(channel.name)
        .write_str(channel.description)
        .write_u16(len(glob.streams.streams[f"chat/{chan}"].clients))
        .finish(ids.server_channelInfo)
    )


def channel_info_end():
    return b"Y\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00"


def channel_kicked(chan):
    return builder.BinaryWriter().write_str(chan).finish(ids.server_channelKicked)


def silenced_notify(userID):
    return builder.BinaryWriter().write_i32(userID).finish(ids.server_userSilenced)


""" Spectator packets """


def spectator_add(userID):
    return builder.BinaryWriter().write_i32(userID).finish(ids.server_spectatorJoined)


def spectator_remove(userID):
    return builder.BinaryWriter().write_i32(userID).finish(ids.server_spectatorLeft)


def spectator_frames(data):
    return builder.BinaryWriter().write_raw(data).finish(ids.server_spectateFrames)


def spectator_song_missing(userID):
    return (
        builder.BinaryWriter()
        .write_i32(userID)
        .finish(ids.server_spectatorCantSpectate)
    )


def spectator_comrade_joined(user_id: int) -> bytes:
    return (
        builder.BinaryWriter()
        .write_i32(user_id)
        .finish(ids.server_fellowSpectatorJoined)
    )


def spectator_comrade_left(userID):
    return (
        builder.BinaryWriter().write_i32(userID).finish(ids.server_fellowSpectatorLeft)
    )


""" Multiplayer Packets """


def match_create(matchID):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    matchData = match.getMatchData(censored=True)

    writer = builder.BinaryWriter()
    for data, data_type in matchData:
        builder._writer_from_type(data_type)(writer, data)
    return writer.finish(ids.server_newMatch)


# TODO: Add match object argument to save some CPU
def match_update(matchID, censored=False):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    matchData = match.getMatchData(censored=censored)

    writer = builder.BinaryWriter()
    for data, data_type in matchData:
        builder._writer_from_type(data_type)(writer, data)
    return writer.finish(ids.server_updateMatch)


def match_start(matchID: int):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    matchData = match.getMatchData()

    writer = builder.BinaryWriter()
    for data, data_type in matchData:
        builder._writer_from_type(data_type)(writer, data)
    return writer.finish(ids.server_matchStart)


def match_dispose(matchID):
    return builder.BinaryWriter().write_i32(matchID).finish(ids.server_disposeMatch)


def match_join_success(matchID):
    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return b""

    # Get match binary data and build packet
    match = glob.matches.matches[matchID]
    matchData = match.getMatchData()

    writer = builder.BinaryWriter()
    for data, data_type in matchData:
        builder._writer_from_type(data_type)(writer, data)
    return writer.finish(ids.server_matchJoinSuccess)


def match_join_fail():
    return b"%\x00\x00\x00\x00\x00\x00"


def match_change_password(newPassword):
    return (
        builder.BinaryWriter()
        .write_str(newPassword)
        .finish(ids.server_matchChangePassword)
    )


def match_all_players_loaded():
    return b"5\x00\x00\x00\x00\x00\x00"


def match_player_skipped(userID):
    return (
        builder.BinaryWriter().write_i32(userID).finish(ids.server_matchPlayerSkipped)
    )


def match_all_skipped():
    return b"=\x00\x00\x00\x00\x00\x00"


def match_frames(
    time: int,
    slot_id: int,
    count_300: int,
    count_100: int,
    count_50: int,
    count_geki: int,
    count_katu: int,
    count_miss: int,
    total_score: int,
    max_combo: int,
    current_combo: int,
    perfect: int,
    current_hp: int,
    tag_byte: int,
    using_score_v2: int,
) -> bytes:
    return (
        builder.BinaryWriter()
        .write_i32(time)
        .write_u8(slot_id)
        .write_u16(count_300)
        .write_u16(count_100)
        .write_u16(count_50)
        .write_u16(count_geki)
        .write_u16(count_katu)
        .write_u16(count_miss)
        .write_i32(total_score)
        .write_u16(max_combo)
        .write_u16(current_combo)
        .write_u8(perfect)
        .write_u8(current_hp)
        .write_u8(tag_byte)
        .write_u8(using_score_v2)
        .finish(ids.server_matchScoreUpdate)
    )


def match_complete():
    return b":\x00\x00\x00\x00\x00\x00"


def match_player_fail(slotID):
    return builder.BinaryWriter().write_i32(slotID).finish(ids.server_matchPlayerFailed)


def match_new_host_notify():
    return b"2\x00\x00\x00\x00\x00\x00"


def match_abort():
    return b"j\x00\x00\x00\x00\x00\x00"


""" Other packets """


def server_switch(address):
    return builder.BinaryWriter().write_str(address).finish(ids.server_switchServer)


def notification(message):
    return builder.BinaryWriter().write_str(message).finish(ids.server_notification)


def server_restart(msUntilReconnection):
    return (
        builder.BinaryWriter().write_i32(msUntilReconnection).finish(ids.server_restart)
    )


def rtx(message):
    return builder.BinaryWriter().write_str(message).finish(0x69)


def crash():
    # return buildPacket(ids.server_supporterGMT, ((128, types.UINT32))) + buildPacket(ids.server_ping)
    return b"G\x00\x00\x04\x00\x00\x00\x80\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00"
