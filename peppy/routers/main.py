from __future__ import annotations

import logging
import sys
import traceback
from typing import Optional

import settings
from constants import exceptions
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
from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import Response as FastAPIResponse
from objects import glob
from packets import ids
from packets import reader
from packets import server

logger = logging.getLogger(__name__)

router = APIRouter()

packetsRestricted = [
    ids.client_logout,
    ids.client_userStatsRequest,
    ids.client_requestStatusUpdate,
    ids.client_userPanelRequest,
    ids.client_changeAction,
    ids.client_channelJoin,
    ids.client_channelPart,
]

eventHandler = {
    ids.client_changeAction: changeActionEvent,
    ids.client_logout: logoutEvent,
    ids.client_friendAdd: friendAddEvent,
    ids.client_friendRemove: friendRemoveEvent,
    ids.client_userStatsRequest: userStatsRequestEvent,
    ids.client_requestStatusUpdate: requestStatusUpdateEvent,
    ids.client_userPanelRequest: userPanelRequestEvent,
    ids.client_channelJoin: channelJoinEvent,
    ids.client_channelPart: channelPartEvent,
    ids.client_sendPublicMessage: sendPublicMessageEvent,
    ids.client_sendPrivateMessage: sendPrivateMessageEvent,
    ids.client_setAwayMessage: setAwayMessageEvent,
    ids.client_startSpectating: startSpectatingEvent,
    ids.client_stopSpectating: stopSpectatingEvent,
    ids.client_cantSpectate: cantSpectateEvent,
    ids.client_spectateFrames: spectateFramesEvent,
    ids.client_joinLobby: joinLobbyEvent,
    ids.client_partLobby: partLobbyEvent,
    ids.client_createMatch: createMatchEvent,
    ids.client_joinMatch: joinMatchEvent,
    ids.client_partMatch: partMatchEvent,
    ids.client_matchChangeSlot: changeSlotEvent,
    ids.client_matchChangeSettings: changeMatchSettingsEvent,
    ids.client_matchChangePassword: changeMatchPasswordEvent,
    ids.client_matchChangeMods: changeMatchModsEvent,
    ids.client_matchReady: matchReadyEvent,
    ids.client_matchNotReady: matchReadyEvent,
    ids.client_matchLock: matchLockEvent,
    ids.client_matchStart: matchStartEvent,
    ids.client_matchLoadComplete: matchPlayerLoadEvent,
    ids.client_matchSkipRequest: matchSkipEvent,
    ids.client_matchScoreUpdate: matchFramesEvent,
    ids.client_matchComplete: matchCompleteEvent,
    ids.client_matchNoBeatmap: matchNoBeatmapEvent,
    ids.client_matchHasBeatmap: matchHasBeatmapEvent,
    ids.client_matchTransferHost: matchTransferHostEvent,
    ids.client_matchFailed: matchFailedEvent,
    ids.client_matchChangeTeam: matchChangeTeamEvent,
    ids.client_invite: matchInviteEvent,
    ids.client_tournamentMatchInfoRequest: tournamentMatchInfoRequestEvent,
    ids.client_tournamentJoinMatchChannel: tournamentJoinMatchChannelEvent,
    ids.client_tournamentLeaveMatchChannel: tournamentLeaveMatchChannelEvent,
    ids.client_beatmapInfoRequest: beatmapInfoRequest,
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

                packet_id = reader.read_packet_id(left_data)
                data_length = reader.read_packet_length(left_data)
                packet_data = request_data[pos : (pos + data_length + 7)]

                if packet_id != ids.client_requestStatusUpdate:
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
            response_data = server.server_restart(1)
            response_data += server.notification(
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
