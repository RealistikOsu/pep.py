from __future__ import annotations

from common.constants import mods
from constants import clientPackets
from constants import serverPackets
from logger import log
from objects import glob


def handle(userToken, packetData):
    # Get usertoken data
    userID = userToken.userID
    username = userToken.username

    # Make sure we are not banned
    # if userUtils.isBanned(userID):
    #     userToken.enqueue(serverPackets.login_banned())
    #     return

    # Send restricted message if needed
    # if userToken.restricted:
    #     userToken.checkRestricted(True)

    # Change action packet
    packetData = clientPackets.userActionChange(packetData)

    # If we are not in spectate status but we're spectating someone, stop spectating
    """
if userToken.spectating != 0 and userToken.actionID != actions.WATCHING and userToken.actionID != actions.IDLE and userToken.actionID != actions.AFK:
    userToken.stopSpectating()

# If we are not in multiplayer but we are in a match, part match
if userToken.matchID != -1 and userToken.actionID != actions.MULTIPLAYING and userToken.actionID != actions.MULTIPLAYER and userToken.actionID != actions.AFK:
    userToken.partMatch()
        """

    # Update cached stats if our pp changed if we've just submitted a score or we've changed gameMode
    # if (userToken.actionID == actions.PLAYING or userToken.actionID == actions.MULTIPLAYING) or (userToken.pp != userUtils.getPP(userID, userToken.gameMode)) or (userToken.gameMode != packetData["gameMode"]):

    # Update cached stats if we've changed gamemode
    if userToken.gameMode != packetData["gameMode"]:
        userToken.gameMode = packetData["gameMode"]
        userToken.updateCachedStats()

    # Always update action id, text, md5 and beatmapID
    userToken.actionID = packetData["actionID"]
    userToken.actionMd5 = packetData["actionMd5"]
    userToken.actionMods = packetData["actionMods"]
    userToken.beatmapID = packetData["beatmapID"]

    if userToken.actionID != 1:
        if packetData["actionMods"] & 128:
            # Only reload on mode change.
            if not userToken.relaxing:
                userToken.updateCachedStats()
            userToken.relaxing = True
            userToken.autopiloting = False
            userToken.updateCachedStats()
        # autopiloten
        elif packetData["actionMods"] & 8192:
            # Only reload on mode change.
            if not userToken.autopiloting:
                userToken.updateCachedStats()
            userToken.autopiloting = True
            userToken.relaxing = False
            userToken.updateCachedStats()
        else:
            if (not userToken.autopiloting) and (not userToken.relaxing):
                userToken.updateCachedStats()
            userToken.relaxing = False
            userToken.autopiloting = False
            userToken.updateCachedStats()

    prefix = "VN"
    if userToken.relaxing:
        prefix = "RX"
    elif userToken.autopiloting:
        prefix = "AP"

    # User Statuses! Apply only on IDLE/AFK
    if userToken.actionID in (0, 1):
        # These should not have actionText
        status = glob.user_statuses.get_status_if_enabled(userID)
        if status:
            userToken.actionText = f"({status.status}) [{prefix}]"
        else:
            userToken.actionText = f"[{prefix}]"
    else:
        userToken.actionText = f"[{prefix}] " + packetData["actionText"]

    # Enqueue our new user panel and stats to us and our spectators
    p = serverPackets.user_presence(userID) + serverPackets.user_stats(userID)
    userToken.enqueue(p)
    if userToken.spectators:
        for i in userToken.spectators:
            glob.tokens.tokens[i].enqueue(p)

    # Console output
    log.info(
        f"{username} updated their presence! [Action ID: {userToken.actionID} // Action Text: {userToken.actionText}]",
    )
