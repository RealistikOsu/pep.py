import datetime
import sys
import traceback

import tornado.gen
import tornado.web

from logger import log
from common.web import requestsManager
from constants import exceptions
from constants import packetIDs
from constants import serverPackets
from events import cantSpectateEvent
from events import changeActionEvent
from events import changeMatchModsEvent
from events import changeMatchPasswordEvent
from events import changeMatchSettingsEvent
from events import changeSlotEvent
from events import channelJoinEvent
from events import channelPartEvent
from events import createMatchEvent
from events import friendAddEvent
from events import friendRemoveEvent
from events import joinLobbyEvent
from events import joinMatchEvent
from events import loginEvent
from events import logoutEvent
from events import matchChangeTeamEvent
from events import matchCompleteEvent
from events import matchFailedEvent
from events import matchFramesEvent
from events import matchHasBeatmapEvent
from events import matchInviteEvent
from events import matchLockEvent
from events import matchNoBeatmapEvent
from events import matchPlayerLoadEvent
from events import matchReadyEvent
from events import matchSkipEvent
from events import matchStartEvent
from events import matchTransferHostEvent
from events import partLobbyEvent
from events import partMatchEvent
from events import requestStatusUpdateEvent
from events import sendPrivateMessageEvent
from events import sendPublicMessageEvent
from events import setAwayMessageEvent
from events import spectateFramesEvent
from events import startSpectatingEvent
from events import stopSpectatingEvent
from events import userPanelRequestEvent
from events import userStatsRequestEvent
from events import tournamentMatchInfoRequestEvent
from events import tournamentJoinMatchChannelEvent
from events import tournamentLeaveMatchChannelEvent
from events import beatmapInfoRequest
from helpers import packetHelper
from objects import glob
from config import config

# Placing this here so we do not have to register this every conn.

# Packets processed if in restricted mode.
# All other packets will be ignored if the user is in restricted mode
packetsRestricted = [
    packetIDs.client_logout,
    packetIDs.client_userStatsRequest,
    packetIDs.client_requestStatusUpdate,
    packetIDs.client_userPanelRequest,
    packetIDs.client_changeAction,
    packetIDs.client_channelJoin,
    packetIDs.client_channelPart,
]

eventHandler = {
    packetIDs.client_changeAction: (changeActionEvent),
    packetIDs.client_logout: (logoutEvent),
    packetIDs.client_friendAdd: (friendAddEvent),
    packetIDs.client_friendRemove: (friendRemoveEvent),
    packetIDs.client_userStatsRequest: (userStatsRequestEvent),
    packetIDs.client_requestStatusUpdate: (requestStatusUpdateEvent),
    packetIDs.client_userPanelRequest: (userPanelRequestEvent),
    packetIDs.client_channelJoin: (channelJoinEvent),
    packetIDs.client_channelPart: (channelPartEvent),
    packetIDs.client_sendPublicMessage: (sendPublicMessageEvent),
    packetIDs.client_sendPrivateMessage: (sendPrivateMessageEvent),
    packetIDs.client_setAwayMessage: (setAwayMessageEvent),
    packetIDs.client_startSpectating: (startSpectatingEvent),
    packetIDs.client_stopSpectating: (stopSpectatingEvent),
    packetIDs.client_cantSpectate: (cantSpectateEvent),
    packetIDs.client_spectateFrames: (spectateFramesEvent),
    packetIDs.client_joinLobby: (joinLobbyEvent),
    packetIDs.client_partLobby: (partLobbyEvent),
    packetIDs.client_createMatch: (createMatchEvent),
    packetIDs.client_joinMatch: (joinMatchEvent),
    packetIDs.client_partMatch: (partMatchEvent),
    packetIDs.client_matchChangeSlot: (changeSlotEvent),
    packetIDs.client_matchChangeSettings: (changeMatchSettingsEvent),
    packetIDs.client_matchChangePassword: (changeMatchPasswordEvent),
    packetIDs.client_matchChangeMods: (changeMatchModsEvent),
    packetIDs.client_matchReady: (matchReadyEvent),
    packetIDs.client_matchNotReady: (matchReadyEvent),
    packetIDs.client_matchLock: (matchLockEvent),
    packetIDs.client_matchStart: (matchStartEvent),
    packetIDs.client_matchLoadComplete: (matchPlayerLoadEvent),
    packetIDs.client_matchSkipRequest: (matchSkipEvent),
    packetIDs.client_matchScoreUpdate: (matchFramesEvent),
    packetIDs.client_matchComplete: (matchCompleteEvent),
    packetIDs.client_matchNoBeatmap: (matchNoBeatmapEvent),
    packetIDs.client_matchHasBeatmap: (matchHasBeatmapEvent),
    packetIDs.client_matchTransferHost: (matchTransferHostEvent),
    packetIDs.client_matchFailed: (matchFailedEvent),
    packetIDs.client_matchChangeTeam: (matchChangeTeamEvent),
    packetIDs.client_invite: (matchInviteEvent),
    packetIDs.client_tournamentMatchInfoRequest: (tournamentMatchInfoRequestEvent),
    packetIDs.client_tournamentJoinMatchChannel: (tournamentJoinMatchChannelEvent),
    packetIDs.client_tournamentLeaveMatchChannel: (tournamentLeaveMatchChannelEvent),
    packetIDs.client_beatmapInfoRequest: (beatmapInfoRequest),
}


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncPost(self):

        # Client's token string and request data
        requestTokenString = self.request.headers.get("osu-token")
        requestData = self.request.body

        # Server's token string and request data
        responseTokenString = ""
        responseData = bytes()

        if requestTokenString is None:
            # No token, first request. Handle login.
            responseTokenString, responseData = loginEvent.handle(self)
        else:
            userToken = None
            try:
                # This is not the first packet, send response based on client's request
                # Packet start position, used to read stacked packets
                pos = 0

                # Make sure the token exists
                if requestTokenString not in glob.tokens.tokens:
                    raise exceptions.tokenNotFoundException()

                # Token exists, get its object and lock it
                userToken = glob.tokens.tokens[requestTokenString]
                userToken.processingLock.acquire()

                # Keep reading packets until everything has been read
                while pos < len(requestData):
                    # Get packet from stack starting from new packet
                    leftData = requestData[pos:]

                    # Get packet ID, data length and data
                    packetID = packetHelper.readPacketID(leftData)
                    dataLength = packetHelper.readPacketLength(leftData)
                    packetData = requestData[pos:(pos+dataLength+7)]

                    # Process/ignore packet
                    if packetID != 4:
                        if packetID in eventHandler:
                            if not userToken.restricted or (userToken.restricted and packetID in packetsRestricted):
                                eventHandler[packetID].handle(userToken, packetData)
                            else:
                                log.warning("Ignored packet id from {} ({}) (user is restricted)".format(requestTokenString, packetID))
                        else:
                            log.warning("Unknown packet id from {} ({})".format(requestTokenString, packetID))

                    # Update pos so we can read the next stacked packet
                    # +7 because we add packet ID bytes, unused byte and data length bytes
                    pos += dataLength+7

                # Token queue built, send it
                responseTokenString = userToken.token
                responseData = userToken.fetch_queue()
            except exceptions.tokenNotFoundException:
                # Token not found. Get the user to be reconnected.
                responseData = serverPackets.server_restart(1)
                responseData += serverPackets.notification(
                    f"You don't seem to be logged into {config.SRV_NAME} anymore... "
                    "This is common during server restarts, trying to log you back in."
                )
                log.warning("Received unknown token! This is normal during server restarts. Reconnecting them.")
            finally:
                # Unlock token
                if userToken is not None:
                    # Update ping time for timeout
                    userToken.updatePingTime()
                    # Release processing lock
                    userToken.processingLock.release()
                    # Delete token if kicked
                    if userToken.kicked:
                        glob.tokens.deleteToken(userToken)

        # Send server's response to client
        # We don't use token object because we might not have a token (failed login)


        self.write(responseData)

        # Add all the headers AFTER the response has been written
        self.set_status(200)
        self.add_header("cho-token", responseTokenString)
        self.add_header("cho-protocol", "19")
        self.add_header("Connection", "keep-alive")
        self.add_header("Keep-Alive", "timeout=5, max=100")
        self.add_header("Content-Type", "text/html; charset=UTF-8")

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self):
        # We are updating this to be full stealth
        self.write(
            """Loading site... <meta http-equiv="refresh" content="0; URL='https://www.youtube.com/watch?v=dQw4w9WgXcQ'" />"""
        )
