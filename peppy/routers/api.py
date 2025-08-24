from __future__ import annotations

import logging
import random
from typing import Optional

import settings
from fastapi import APIRouter
from pydantic import BaseModel
from objects import glob

logger = logging.getLogger(__name__)

router = APIRouter()


class OnlineUsersResponse(BaseModel):
    status: int
    message: str
    result: int


class ServerStatusResponse(BaseModel):
    status: int
    message: str
    result: int


class Beatmap(BaseModel):
    id: int
    md5: str
    mods: int


class UserAction(BaseModel):
    id: int
    text: str
    beatmap: Beatmap


class UserStatusResponse(BaseModel):
    code: int
    username: str
    user_id: int
    privileges: int
    action: UserAction
    match_id: int
    mode: int
    rank: int
    autopilot: bool
    relax: bool


class InfosResponse(BaseModel):
    version: int
    motd: str
    onlineUsers: int
    icon: str
    botID: int


@router.get("/v1/onlineUsers", response_model=OnlineUsersResponse)
async def online_users_handler() -> OnlineUsersResponse:
    """Handle online users API endpoint."""
    return OnlineUsersResponse(status=200, message="ok", result=len(glob.tokens.tokens))


@router.get("/v1/serverStatus", response_model=ServerStatusResponse)
async def server_status_handler() -> ServerStatusResponse:
    """Handle server status API endpoint."""
    return ServerStatusResponse(
        status=200, message="ok", result=-1 if glob.restarting else 1
    )


@router.get("/status/{user_id}", response_model=Optional[UserStatusResponse])
async def api_status_handler(user_id: int) -> Optional[UserStatusResponse]:
    """Handle API status endpoint."""
    token = glob.tokens.getTokenFromUserID(user_id)

    if not token:
        return None

    return UserStatusResponse(
        code=200,
        username=token.username,
        user_id=token.userID,
        privileges=token.privileges,
        action=UserAction(
            id=token.actionID,
            text=token.actionText,
            beatmap=Beatmap(
                id=token.beatmapID,
                md5=token.actionMd5,
                mods=token.actionMods,
            ),
        ),
        match_id=token.matchID,
        mode=token.gameMode,
        rank=token.gameRank,
        autopilot=token.autopiloting,
        relax=token.relaxing,
    )


@router.get("/v2/status/{user_id}", response_model=Optional[UserStatusResponse])
async def api_status_v2_handler(user_id: int) -> Optional[UserStatusResponse]:
    """Handle API status v2 endpoint."""
    token = glob.tokens.getTokenFromUserID(user_id)

    if not token:
        return None

    return UserStatusResponse(
        code=200,
        username=token.username,
        user_id=token.userID,
        privileges=token.privileges,
        action=UserAction(
            id=token.actionID,
            text=token.actionText,
            beatmap=Beatmap(
                id=token.beatmapID,
                md5=token.actionMd5,
                mods=token.actionMods,
            ),
        ),
        match_id=token.matchID,
        mode=token.gameMode,
        rank=token.gameRank,
        autopilot=token.autopiloting,
        relax=token.relaxing,
    )


@router.get("/infos", response_model=InfosResponse)
async def infos_handler() -> InfosResponse:
    """Handles the server info endpoint for the Aeris client."""
    return InfosResponse(
        version=0,
        motd=f"{settings.PS_NAME}\n" + random.choice(glob.banchoConf.config["Quotes"]),
        onlineUsers=len(glob.tokens.tokens),
        icon="https://ussr.pl/static/image/newlogo2.png",
        botID=settings.PS_BOT_USER_ID,
    )
