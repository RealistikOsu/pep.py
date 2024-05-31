from __future__ import annotations

import threading
import time
from typing import Optional

import redis

from common.ripple import userUtils
from config import config
from constants import serverPackets
from constants.exceptions import periodicLoopException
from events import logoutEvent
from helpers.user_helper import username_safe
from logger import log
from objects import glob
from objects.osuToken import UserToken


class TokenList:
    def __init__(self):
        self.tokens: dict[str, UserToken] = {}
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    def addToken(
        self,
        userID,
        ip="",
        irc=False,
        timeOffset: int = 0,
        tournament: bool = False,
    ) -> UserToken:
        """
        Add a token object to tokens list

        :param userID: user id associated to that token
        :param ip: ip address of the client
        :param irc: if True, set this token as IRC client
        :param timeOffset: the time offset from UTC for this user. Default: 0.
        :param tournament: if True, flag this client as a tournement client. Default: True.
        :return: token object
        """
        newToken = UserToken(
            userID,
            ip=ip,
            irc=irc,
            timeOffset=timeOffset,
            tournament=tournament,
        )
        self.tokens[newToken.token] = newToken
        glob.redis.set("ripple:online_users", len(self.tokens))
        return newToken

    def deleteToken(self, token: UserToken) -> None:
        """
        Delete a token from token list if it exists

        :param token: token string
        :return:
        """
        if token in self.tokens:
            if self.tokens[token].ip:
                userUtils.deleteBanchoSessions(
                    self.tokens[token].userID,
                    self.tokens[token].ip,
                )
            t = self.tokens.pop(token)
            glob.redis.set("ripple:online_users", len(glob.tokens.tokens))

    def getUserIDFromToken(self, token: str) -> Optional[int]:
        """
        Get user ID from a token

        :param token: token to find
        :return: False if not found, userID if found
        """
        # Make sure the token exists
        user = self.tokens.get(token)
        return user.userID if user else None

    def getTokenFromUserID(self, userID: int) -> Optional[UserToken]:
        """
        Get token from a user ID

        :param userID: user ID to find
        :return: None if not found, token object if found
        """
        userID = int(userID)
        for value in self.tokens.values():
            if value.userID == userID:
                return value

    def getTokenFromUsername(
        self,
        username: str,
        safe: bool = False,
    ) -> Optional[UserToken]:
        """
        Get an osuToken object from an username

        :param username: normal username or safe username
        :param safe:     if True, username is a safe username,
                                        compare it with token's safe username rather than normal username
        :return: osuToken object or None
        """

        if not safe:
            username = username_safe(username)

        for user in self.tokens.values():
            if user.safeUsername == username:
                return user

    def deleteOldTokens(self, userID: int) -> None:
        """
        Delete old userID's tokens if found

        :param userID: tokens associated to this user will be deleted
        :return:
        """
        # Delete older tokens
        for key, value in list(self.tokens.items()):
            if value.userID == userID:
                # Delete this token from the dictionary
                # self.tokens[key].kick("You have logged in from somewhere else. You can't connect to Bancho/IRC from more than one device at the same time.", "kicked, multiple clients")
                logoutEvent.handle(self.tokens[key])

    def multipleEnqueue(self, packet: bytes, who: list[int], but: bool = False) -> None:
        """
        Enqueue a packet to multiple users

        :param packet: packet bytes to enqueue
        :param who: userIDs array
        :param but: if True, enqueue to everyone but users in `who` array
        :return:
        """
        for value in self.tokens.values():
            if (value.userID in who and not but) or (value.userID not in who and but):
                value.enqueue(packet)

    def enqueueAll(self, packet: bytes) -> None:
        """
        Enqueue packet(s) to every connected user

        :param packet: packet bytes to enqueue
        :return:
        """
        for value in self.tokens.values():
            value.enqueue(packet)

    def usersTimeoutCheckLoop(self) -> None:
        """
        Start timed out users disconnect loop.
        This function will be called every `checkTime` seconds and so on, forever.
        CALL THIS FUNCTION ONLY ONCE!
        :return:
        """
        try:
            log.debug("Checking timed out clients")
            exceptions = []
            timeoutLimit = int(time.time()) - 100
            for key, value in self.tokens.items():
                # Check timeout (fokabot is ignored)
                if (
                    value.pingTime < timeoutLimit
                    and value.userID != config.SRV_BOT_ID
                    and not value.irc
                    and not value.tournament
                ):
                    # That user has timed out, add to disconnected tokens
                    # We can't delete it while iterating or items() throws an error
                    log.debug(f"{value.username} timed out!!")
                    value.enqueue(
                        serverPackets.notification(
                            "Your connection to the server timed out.",
                        ),
                    )
                    try:
                        logoutEvent.handle(value)
                    except Exception as e:
                        exceptions.append(e)
                        log.error(
                            "Something wrong happened while disconnecting a timed out client.",
                        )

            # Re-raise exceptions if needed
            if exceptions:
                raise periodicLoopException(exceptions)
        finally:
            # Schedule a new check (endless loop)
            threading.Timer(100, self.usersTimeoutCheckLoop).start()

    def spamProtectionResetLoop(self) -> None:
        """
        Start spam protection reset loop.
        Called every 10 seconds.
        CALL THIS FUNCTION ONLY ONCE!

        :return:
        """
        try:
            # Reset spamRate for every token
            for value in self.tokens.values():
                value.spamRate = 0
        finally:
            # Schedule a new check (endless loop)
            threading.Timer(10, self.spamProtectionResetLoop).start()

    def deleteBanchoSessions(self) -> None:
        """
        Remove all `peppy:sessions:*` redis keys.
        Call at bancho startup to delete old cached sessions

        :return:
        """
        try:
            # TODO: Make function or some redis meme
            glob.redis.eval(
                "return redis.call('del', unpack(redis.call('keys', ARGV[1])))",
                0,
                "peppy:sessions:*",
            )
        except redis.RedisError:
            pass
