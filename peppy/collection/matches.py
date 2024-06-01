from __future__ import annotations

import threading
import time

from constants import serverPackets
from constants.exceptions import periodicLoopException
from logger import log
from objects import glob
from objects.match import Match


class MatchList:
    def __init__(self):
        """Initialize a matchList object"""
        self.matches: dict[int, Match] = {}
        self.lastID = 1

    def createMatch(
        self,
        matchName: str,
        matchPassword: str,
        beatmapID: int,
        beatmapName: str,
        beatmapMD5: str,
        gameMode: int,
        hostUserID: int,
        isTourney=False,
    ) -> int:
        """
        Add a new match to matches list

        :param matchName: match name, string
        :param matchPassword: match md5 password. Leave empty for no password
        :param beatmapID: beatmap ID
        :param beatmapName: beatmap name, string
        :param beatmapMD5: beatmap md5 hash, string
        :param gameMode: game mode ID. See gameModes.py
        :param hostUserID: user id of who created the match
        :return: match ID
        """
        # Add a new match to matches list and create its stream
        matchID = self.lastID
        self.lastID += 1
        self.matches[matchID] = Match(
            matchID,
            matchName,
            matchPassword,
            beatmapID,
            beatmapName,
            beatmapMD5,
            gameMode,
            hostUserID,
            isTourney,
        )
        return matchID

    def match_dispose(self, matchID: int) -> None:
        """
        Destroy match object with id = matchID

        :param matchID: ID of match to dispose
        :return:
        """
        # Make sure the match exists
        if matchID not in self.matches:
            return

        # Get match and disconnect all players
        _match = self.matches[matchID]
        for slot in _match.slots:
            _token = glob.tokens.getTokenFromUserID(slot.userID)
            if _token is None:
                continue
            _match.userLeft(
                _token,
                disposeMatch=False,
            )  # don't dispose the match twice when we remove all players

        # Delete chat channel
        glob.channels.removeChannel(f"#multi_{matchID}")

        # Send matchDisposed packet before disposing streams
        glob.streams.broadcast(_match.streamName, serverPackets.match_dispose(matchID))

        # Dispose all streams
        glob.streams.dispose(_match.streamName)
        glob.streams.dispose(_match.playingStreamName)
        glob.streams.remove(_match.streamName)
        glob.streams.remove(_match.playingStreamName)

        # Send match dispose packet to everyone in lobby
        glob.streams.broadcast("lobby", serverPackets.match_dispose(matchID))
        del self.matches[matchID]
        log.info(f"MPROOM{matchID}: Room disposed manually")

    def cleanupLoop(self) -> None:
        """
        Start match cleanup loop.
        Empty matches that have been created more than 60 seconds ago will get deleted.
        Useful when people create useless lobbies with `!mp make`.
        The check is done every 30 seconds.
        This method starts an infinite loop, call it only once!
        :return:
        """
        try:
            log.debug("Checking empty matches")
            t = int(time.time())
            emptyMatches = []
            exceptions = []

            # Collect all empty matches
            for m in self.matches.values():
                if [x for x in m.slots if x.user is not None]:
                    continue
                if t - m.createTime >= 120:
                    log.debug(f"Match #{m.matchID} marked for cleanup")
                    emptyMatches.append(m.matchID)

            # Dispose all empty matches
            for matchID in emptyMatches:
                try:
                    self.match_dispose(matchID)
                except Exception as e:
                    exceptions.append(e)
                    log.error(
                        "Something wrong happened while disposing a timed out match.",
                    )

            # Re-raise exception if needed
            if exceptions:
                raise periodicLoopException(exceptions)
        finally:
            # Schedule a new check (endless loop)
            threading.Timer(30, self.cleanupLoop).start()
