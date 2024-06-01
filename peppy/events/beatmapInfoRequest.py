from __future__ import annotations

from common.ripple.userUtils import restrict_with_log
from objects.osuToken import UserToken


def handle(token: UserToken, _) -> None:
    restrict_with_log(
        token.userID,
        "Outdated client bypassing login gate",
        "The user has send a beatmap request packet, which has been removed "
        "since ~2020. This means that they likely have a client with a version "
        "changer to bypass the login gate. (bancho gate)",
    )
