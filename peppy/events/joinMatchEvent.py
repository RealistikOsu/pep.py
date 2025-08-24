from __future__ import annotations

import logging

from constants import exceptions
from objects import glob
from packets import client
from packets import server

logger = logging.getLogger(__name__)


def handle(userToken, packetData):
    # read packet data
    packetData = client.joinMatch(packetData)
    matchID = packetData["matchID"]
    password = packetData["password"]

    # Get match from ID
    try:
        # Make sure the match exists
        if matchID not in glob.matches.matches:
            return

        # Hash password if needed
        # if password != "":
        #     password = generalUtils.stringMd5(password)

        # Check password
        with glob.matches.matches[matchID] as match:
            if match.matchPassword != "" and match.matchPassword != password:
                raise exceptions.matchWrongPasswordException()

            # Password is correct, join match
            userToken.joinMatch(matchID)
    except exceptions.matchWrongPasswordException:
        userToken.enqueue(server.match_join_fail())
        logger.warning(
            "{} has tried to join a mp room, but he typed the wrong password".format(
                userToken.username,
            ),
        )
