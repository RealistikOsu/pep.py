from __future__ import annotations

import logging
import sys
import traceback
from typing import Optional

import settings
from fastapi import APIRouter, Request
from fastapi.responses import Response as FastAPIResponse
from constants import exceptions
from constants import packetIDs
from constants import serverPackets
from events import beatmapInfoRequest
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
from events import tournamentJoinMatchChannelEvent
from events import tournamentLeaveMatchChannelEvent
from events import tournamentMatchInfoRequestEvent
from events import userPanelRequestEvent
from events import userStatsRequestEvent
from helpers import packetHelper
from objects import glob

logger = logging.getLogger(__name__)

router = APIRouter()

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
    packetIDs.client_changeAction: changeActionEvent,
    packetIDs.client_logout: logoutEvent,
    packetIDs.client_friendAdd: friendAddEvent,
    packetIDs.client_friendRemove: friendRemoveEvent,
    packetIDs.client_userStatsRequest: userStatsRequestEvent,
    packetIDs.client_requestStatusUpdate: requestStatusUpdateEvent,
    packetIDs.client_userPanelRequest: userPanelRequestEvent,
    packetIDs.client_channelJoin: channelJoinEvent,
    packetIDs.client_channelPart: channelPartEvent,
    packetIDs.client_sendPublicMessage: sendPublicMessageEvent,
    packetIDs.client_sendPrivateMessage: sendPrivateMessageEvent,
    packetIDs.client_setAwayMessage: setAwayMessageEvent,
    packetIDs.client_startSpectating: startSpectatingEvent,
    packetIDs.client_stopSpectating: stopSpectatingEvent,
    packetIDs.client_cantSpectate: cantSpectateEvent,
    packetIDs.client_spectateFrames: spectateFramesEvent,
    packetIDs.client_joinLobby: joinLobbyEvent,
    packetIDs.client_partLobby: partLobbyEvent,
    packetIDs.client_createMatch: createMatchEvent,
    packetIDs.client_joinMatch: joinMatchEvent,
    packetIDs.client_partMatch: partMatchEvent,
    packetIDs.client_matchChangeSlot: changeSlotEvent,
    packetIDs.client_matchChangeSettings: changeMatchSettingsEvent,
    packetIDs.client_matchChangePassword: changeMatchPasswordEvent,
    packetIDs.client_matchChangeMods: changeMatchModsEvent,
    packetIDs.client_matchReady: matchReadyEvent,
    packetIDs.client_matchNotReady: matchReadyEvent,
    packetIDs.client_matchLock: matchLockEvent,
    packetIDs.client_matchStart: matchStartEvent,
    packetIDs.client_matchLoadComplete: matchPlayerLoadEvent,
    packetIDs.client_matchSkipRequest: matchSkipEvent,
    packetIDs.client_matchScoreUpdate: matchFramesEvent,
    packetIDs.client_matchComplete: matchCompleteEvent,
    packetIDs.client_matchNoBeatmap: matchNoBeatmapEvent,
    packetIDs.client_matchHasBeatmap: matchHasBeatmapEvent,
    packetIDs.client_matchTransferHost: matchTransferHostEvent,
    packetIDs.client_matchFailed: matchFailedEvent,
    packetIDs.client_matchChangeTeam: matchChangeTeamEvent,
    packetIDs.client_invite: matchInviteEvent,
    packetIDs.client_tournamentMatchInfoRequest: tournamentMatchInfoRequestEvent,
    packetIDs.client_tournamentJoinMatchChannel: tournamentJoinMatchChannelEvent,
    packetIDs.client_tournamentLeaveMatchChannel: tournamentLeaveMatchChannelEvent,
    packetIDs.client_beatmapInfoRequest: beatmapInfoRequest,
}


@router.get("/")
async def root_handler() -> Response:
    """Handle root endpoint - redirects to YouTube."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        """Loading site... <meta http-equiv="refresh" content="0; URL='https://www.youtube.com/watch?v=dQw4w9WgXcQ'" />""",
        media_type="text/html",
    )


@router.post("/")
async def main_handler(request: Request) -> Response:
    """Handle main bancho protocol endpoint."""
    request_token_string = request.headers.get("osu-token")
    request_data = await request.body()

    response_token_string = ""
    response_data = b""

    if request_token_string is None:
        response_token_string, response_data = await loginEvent.handle_fastapi(request)
    else:
        user_token = None
        try:
            pos = 0

            if request_token_string not in glob.tokens.tokens:
                raise exceptions.tokenNotFoundException()

            user_token = glob.tokens.tokens[request_token_string]
            user_token.processingLock.acquire()

            while pos < len(request_data):
                left_data = request_data[pos:]

                packet_id = packetHelper.readPacketID(left_data)
                data_length = packetHelper.readPacketLength(left_data)
                packet_data = request_data[pos : (pos + data_length + 7)]

                if packet_id != 4:
                    if packet_id in eventHandler:
                        if not user_token.restricted or (
                            user_token.restricted and packet_id in packetsRestricted
                        ):
                            eventHandler[packet_id].handle(user_token, packet_data)
                        else:
                            logger.warning(
                                "Ignored packet id from user (user is restricted)",
                                extra={
                                    "token": request_token_string,
                                    "packet_id": packet_id,
                                },
                            )
                    else:
                        logger.warning(
                            "Unknown packet id from user",
                            extra={
                                "token": request_token_string,
                                "packet_id": packet_id,
                            },
                        )

                pos += data_length + 7

            response_token_string = user_token.token
            response_data = user_token.fetch_queue()
        except exceptions.tokenNotFoundException:
            response_data = serverPackets.server_restart(1)
            response_data += serverPackets.notification(
                f"You don't seem to be logged into {settings.PS_NAME} anymore... "
                "This is common during server restarts, trying to log you back in.",
            )
            logger.warning(
                "Received unknown token! This is normal during server restarts. Reconnecting them.",
            )
        finally:
            if user_token is not None:
                user_token.updatePingTime()
                user_token.processingLock.release()
                if user_token.kicked:
                    glob.tokens.deleteToken(user_token)

    response = FastAPIResponse(content=response_data)
    response.headers["cho-token"] = response_token_string
    response.headers["cho-protocol"] = "19"
    response.headers["Connection"] = "keep-alive"
    response.headers["Keep-Alive"] = "timeout=5, max=100"
    response.headers["Content-Type"] = "text/html; charset=UTF-8"

    return response
