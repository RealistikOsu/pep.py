from __future__ import annotations

import threading
import time
import uuid
from typing import Optional
from typing import TYPE_CHECKING

from common.constants import actions
from common.constants import gameModes
from common.constants import privileges
from common.ripple import userUtils
from config import config
from constants import exceptions
from constants import serverPackets
from constants.rosuprivs import ADMIN_PRIVS
from events import logoutEvent
from helpers import chatHelper as chat
from logger import log
from objects import glob

if TYPE_CHECKING:
    from objects.channel import Channel


class UserToken:
    def __init__(
        self,
        userID,
        token_=None,
        ip="",
        irc=False,
        timeOffset=0,
        tournament=False,
    ):
        """
        Create a token object and set userID and token

        :param userID: user associated to this token
        :param token_:     if passed, set token to that value
                                        if not passed, token will be generated
        :param ip: client ip. optional.
        :param irc: if True, set this token as IRC client. Default: False.
        :param timeOffset: the time offset from UTC for this user. Default: 0.
        :param tournament: if True, flag this client as a tournement client. Default: True.
        """
        # Set stuff
        self.userID = userID

        # Using MySQL over 5 billion SQL queries
        data_db = glob.db.fetch(
            "SELECT `username`, `username_safe`, `privileges`, `silence_end` FROM users WHERE id = %s LIMIT 1",
            (self.userID,),
        )
        self.username = data_db["username"]
        self.safeUsername = data_db["username_safe"]
        self.privileges = int(data_db["privileges"])
        self.silenceEndTime = int(data_db["silence_end"])

        self.irc = irc
        self.kicked = False
        self.loginTime = int(time.time())
        self.pingTime = self.loginTime
        self.timeOffset = timeOffset
        self.streams = []
        self.tournament = tournament
        self.messagesBuffer = []

        # Default variables
        self.spectators = []

        # TODO: Move those two vars to a class
        self.spectating = None
        self.spectatingUserID = 0  # we need this in case we the host gets DCed

        self.joinedChannels = []
        self.ip = ip
        self.country = 0
        self.location = [0.0, 0.0]
        self.awayMessage = ""
        self.sentAway = []
        self.matchID = -1
        self.tillerino = [0, 0, -1.0]  # beatmap, mods, acc
        self.silenceEndTime = 0
        self.queue = bytearray()

        # Spam protection
        self.spamRate = 0

        # Stats cache
        self.actionID = actions.IDLE
        self.actionText = ""
        self.actionMd5 = ""
        self.actionMods = 0
        self.gameMode = gameModes.STD
        self.beatmapID = 0
        self.rankedScore = 0
        self.accuracy = 0.0
        self.playcount = 0
        self.totalScore = 0
        self.gameRank = 0
        self.pp = 0

        # Relax
        self.relaxing = False
        self.relaxAnnounce = False

        # Autopilot
        self.autopiloting = False
        self.autoAnnounce = False

        # Generate/set token
        if token_ is not None:
            self.token = token_
        else:
            self.token = str(uuid.uuid4())

        # Locks
        self.processingLock = (
            threading.Lock()
        )  # Acquired while there's an incoming packet from this user
        self._bufferLock = threading.Lock()  # Acquired while writing to packets buffer
        self._spectLock = threading.RLock()

        # Set stats
        self.updateCachedStats()

        # If we have a valid ip, save bancho session in DB so we can cache LETS logins
        if ip != "":
            userUtils.saveBanchoSession(self.userID, self.ip)

        # Join main stream
        self.joinStream("main")

    @property
    def restricted(self) -> bool:
        """Bool corresponding to the user's restricted status."""

        return not self.privileges & privileges.USER_PUBLIC

    @property
    def admin(self) -> bool:
        """Bool corresponding to whether the user is important staff or smth."""

        # Hardcode these as we mean and im lazy
        return self.privileges in ADMIN_PRIVS

    @property
    def banned(self) -> bool:
        """Bool corresponding to whether the user is banned from the server."""

        return not self.privileges & privileges.USER_NORMAL

    @property
    def silenced(self) -> bool:
        """Checks if the user is currently silenced."""

        return self.silenceEndTime - time.time() > 0

    def enqueue(self, bytes_: bytes) -> None:
        """
        Add bytes (packets) to queue

        :param bytes_: (packet) bytes to enqueue
        """

        # Stop queuing stuff to the bot so we dont run out of mem
        if self.userID == config.SRV_BOT_ID:
            return

        with self._bufferLock:
            self.queue += bytes_

    def resetQueue(self) -> None:
        """Resets the queue. Call when enqueued packets have been sent"""

        with self._bufferLock:
            self.queue.clear()

    def fetch_queue(self) -> bytes:
        """Manages getting all of the queued packets for the users and clearing
        the queue, alongside managing the type."""

        with self._bufferLock:
            b = bytes(self.queue.copy())
            self.queue.clear()

        return b

    def joinChannel(self, channelObject: Channel):
        """
        Join a channel

        :param channelObject: channel object
        :raises: exceptions.userAlreadyInChannelException()
                         exceptions.channelNoPermissionsException()
        """
        if channelObject.name in self.joinedChannels:
            raise exceptions.userAlreadyInChannelException()
        if not channelObject.publicRead and not self.admin:
            raise exceptions.channelNoPermissionsException()
        self.joinedChannels.append(channelObject.name)
        self.joinStream(f"chat/{channelObject.name}")
        self.enqueue(serverPackets.channel_join_success(channelObject.clientName))

    def partChannel(self, channelObject: Channel):
        """
        Remove channel from joined channels list

        :param channelObject: channel object
        """
        self.joinedChannels.remove(channelObject.name)
        self.leaveStream(f"chat/{channelObject.name}")

    def setLocation(self, latitude: float, longitude: float) -> None:
        """
        Set client location

        :param latitude: latitude
        :param longitude: longitude
        """
        self.location = (latitude, longitude)

    def getLatitude(self) -> float:
        """
        Get latitude

        :return: latitude
        """
        return self.location[0]

    def getLongitude(self) -> float:
        """
        Get longitude

        :return: longitude
        """
        return self.location[1]

    def startSpectating(self, host: UserToken) -> None:
        """
        Set the spectating user to userID, join spectator stream and chat channel
        and send required packets to host

        :param host: host UserToken object
        """
        with self._spectLock:
            # Stop spectating old client
            self.stopSpectating()

            # Set new spectator host
            self.spectating = host.token
            self.spectatingUserID = host.userID

            # Add us to host's spectator list
            host.spectators.append(self.token)

            # Create and join spectator stream
            streamName = f"spect/{host.userID}"
            glob.streams.add(streamName)
            self.joinStream(streamName)
            host.joinStream(streamName)

            # Send spectator join packet to host
            host.enqueue(serverPackets.spectator_add(self.userID))

            # Create and join #spectator (#spect_userid) channel
            glob.channels.addTempChannel(f"#spect_{host.userID}")
            chat.joinChannel(
                token=self,
                channel=f"#spect_{host.userID}",
                force=True,
            )
            if len(host.spectators) == 1:
                # First spectator, send #spectator join to host too
                chat.joinChannel(
                    token=host,
                    channel=f"#spect_{host.userID}",
                    force=True,
                )

            # Send fellow spectator join to all clients
            glob.streams.broadcast(
                streamName,
                serverPackets.spectator_comrade_joined(self.userID),
            )

            # Get current spectators list
            for i in host.spectators:
                if i != self.token and i in glob.tokens.tokens:
                    self.enqueue(
                        serverPackets.spectator_comrade_joined(
                            glob.tokens.tokens[i].userID,
                        ),
                    )

            # Log
            log.info(f"{self.username} is spectating {host.username}")

    def stopSpectating(self) -> None:
        """
        Stop spectating, leave spectator stream and channel
        and send required packets to host

        :return:
        """
        with self._spectLock:
            # Remove our userID from host's spectators
            if self.spectating is None or self.spectatingUserID <= 0:
                return
            if self.spectating in glob.tokens.tokens:
                hostToken = glob.tokens.tokens[self.spectating]
            else:
                hostToken = None
            streamName = f"spect/{self.spectatingUserID}"

            # Remove us from host's spectators list,
            # leave spectator stream
            # and end the spectator left packet to host
            self.leaveStream(streamName)
            if hostToken is not None:
                hostToken.spectators.remove(self.token)
                hostToken.enqueue(serverPackets.spectator_remove(self.userID))

                # and to all other spectators
                for i in hostToken.spectators:
                    if i in glob.tokens.tokens:
                        glob.tokens.tokens[i].enqueue(
                            serverPackets.spectator_comrade_left(self.userID),
                        )

                # If nobody is spectating the host anymore, close #spectator channel
                # and remove host from spect stream too
                if len(hostToken.spectators) == 0:
                    chat.partChannel(
                        token=hostToken,
                        channel=f"#spect_{hostToken.userID}",
                        kick=True,
                        force=True,
                    )
                    hostToken.leaveStream(streamName)

                # Console output
                log.info(
                    "{} is no longer spectating {}. Current spectators: {}".format(
                        self.username,
                        self.spectatingUserID,
                        hostToken.spectators,
                    ),
                )

            # Part #spectator channel
            chat.partChannel(
                token=self,
                channel=f"#spect_{self.spectatingUserID}",
                kick=True,
                force=True,
            )

            # Set our spectating user to 0
            self.spectating = None
            self.spectatingUserID = 0

    def updatePingTime(self) -> None:
        """
        Update latest ping time to current time

        :return:
        """
        self.pingTime = int(time.time())

    def joinMatch(self, matchID: int) -> None:
        """
        Set match to matchID, join match stream and channel

        :param matchID: new match ID
        :return:
        """
        # Match exists, get object
        match = glob.matches.matches.get(matchID)
        if not match:
            return

        # Stop spectating
        self.stopSpectating()

        # Leave other matches
        if self.matchID > -1 and self.matchID != matchID:
            self.leaveMatch()

        # Try to join match
        joined = match.userJoin(self)
        if not joined:
            self.enqueue(serverPackets.match_join_fail())
            return

        # Set matchID, join stream, channel and send packet
        self.matchID = matchID
        self.joinStream(match.streamName)
        chat.joinChannel(
            token=self,
            channel=f"#multi_{self.matchID}",
            force=True,
        )
        self.enqueue(serverPackets.match_join_success(matchID))

        if match.isTourney:
            # Alert the user if we have just joined a tourney match
            self.enqueue(
                serverPackets.notification("You are now in a tournament match."),
            )
            # If an user joins, then the ready status of the match changes and
            # maybe not all users are ready.
            match.sendReadyStatus()

    def leaveMatch(self) -> None:
        """
        Leave joined match, match stream and match channel

        :return:
        """
        # Make sure we are in a match
        if self.matchID == -1:
            return

        # Part #multiplayer channel and streams (/ and /playing)
        chat.partChannel(
            token=self,
            channel=f"#multi_{self.matchID}",
            kick=True,
            force=True,
        )
        self.leaveStream(f"multi/{self.matchID}")
        self.leaveStream(f"multi/{self.matchID}/playing")  # optional

        # Set usertoken match to -1
        leavingMatchID = self.matchID
        self.matchID = -1

        # Make sure the match exists
        if leavingMatchID not in glob.matches.matches:
            return

        # The match exists, get object
        match = glob.matches.matches[leavingMatchID]

        # Set slot to free
        match.userLeft(self)

        if match.isTourney:
            # If an user leaves, then the ready status of the match changes and
            # maybe all users are ready. Or maybe nobody is in the match anymore
            match.sendReadyStatus()

    def kick(
        self,
        message="You have been kicked from the server. Please login again.",
        reason="kick",
    ):
        """
        Kick this user from the server

        :param message: Notification message to send to this user.
                                        Default: "You have been kicked from the server. Please login again."
        :param reason: Kick reason, used in logs. Default: "kick"
        :return:
        """
        # Send packet to target
        log.info(f"{self.username} has been disconnected. ({reason})")
        if message != "":
            self.enqueue(serverPackets.notification(message))
        self.enqueue(serverPackets.login_failed())

        # Logout event
        logoutEvent.handle(self, deleteToken=self.irc)

    def silence(self, seconds=None, reason="", author: Optional[int] = None):
        """
        Silences this user (db, packet and token)

        :param seconds: silence length in seconds. If None, get it from db. Default: None
        :param reason: silence reason. Default: empty string
        :param author: userID of who has silenced the user. Default: the configured bot ID.
        :return:
        """

        if author is None:
            author = config.SRV_BOT_ID

        if seconds is None:
            # Get silence expire from db if needed
            seconds = max(0, userUtils.getSilenceEnd(self.userID) - int(time.time()))
        else:
            # Silence in db and token
            userUtils.silence(self.userID, seconds, reason, author)

        # Silence token
        self.silenceEndTime = int(time.time()) + seconds

        # Send silence packet to user
        self.enqueue(serverPackets.silence_end_notify(seconds))

        # Send silenced packet to everyone else
        glob.streams.broadcast("main", serverPackets.silenced_notify(self.userID))

    def spamProtection(self, increaseSpamRate=True):
        """
        Silences the user if is spamming.

        :param increaseSpamRate: set to True if the user has sent a new message. Default: True
        :return:
        """
        # Increase the spam rate if needed
        if increaseSpamRate:
            self.spamRate += 1

        # Silence the user if needed
        if self.spamRate > 10:
            self.silence(1800, "Spamming (auto spam protection)")

    def getSilenceSecondsLeft(self):
        """
        Returns the seconds left for this user's silence
        (0 if user is not silenced)

        :return: silence seconds left (or 0)
        """
        return max(0, self.silenceEndTime - int(time.time()))

    def updateCachedStats(self):
        """
        Update all cached stats for this token

        :return:
        """

        if self.relaxing:
            stats_relax = userUtils.getUserStatsRx(self.userID, self.gameMode)

            self.gameRank = stats_relax["gameRank"]
            self.pp = stats_relax["pp"]
            self.rankedScore = stats_relax["rankedScore"]
            self.accuracy = stats_relax["accuracy"] / 100
            self.playcount = stats_relax["playcount"]
            self.totalScore = stats_relax["totalScore"]

        elif self.autopiloting:
            stats_ap = userUtils.getUserStatsAP(self.userID, self.gameMode)

            self.gameRank = stats_ap["gameRank"]
            self.pp = stats_ap["pp"]
            self.rankedScore = stats_ap["rankedScore"]
            self.accuracy = stats_ap["accuracy"] / 100
            self.playcount = stats_ap["playcount"]
            self.totalScore = stats_ap["totalScore"]
        else:
            stats = userUtils.getUserStats(self.userID, self.gameMode)

            self.gameRank = stats["gameRank"]
            self.pp = stats["pp"]
            self.rankedScore = stats["rankedScore"]
            self.accuracy = stats["accuracy"] / 100
            self.playcount = stats["playcount"]
            self.totalScore = stats["totalScore"]

    def refresh_privs(self) -> None:
        """Fetches the user's privilege group directly from the db and sets
        it in the obj."""

        self.privileges = int(
            glob.db.fetch(
                "SELECT privileges FROM users WHERE id = %s LIMIT 1",
                [self.userID],
            )["privileges"],
        )

    def checkRestricted(self):
        """
        Check if this token is restricted. If so, send fokabot message

        :return:
        """
        oldRestricted = self.restricted
        self.refresh_privs()

        if self.restricted:
            self.notify_restricted()
        elif not self.restricted and oldRestricted != self.restricted:
            self.notify_unrestricted()

    def checkBanned(self):
        """
        Check if this user is banned. If so, disconnect it.

        :return:
        """

        # Ok so the only place where this is used is right after a priv refresh
        # from db so...
        if userUtils.isBanned(self.userID):
            self.enqueue(serverPackets.login_banned())
            logoutEvent.handle(self, deleteToken=False)

    def notify_restricted(self) -> None:
        """
        Set this token as restricted, send FokaBot message to user
        and send offline packet to everyone

        :return:
        """
        chat.sendMessage(
            glob.BOT_NAME,
            self.username,
            f"Your account has been restricted! Please contact the {config.SRV_NAME} staff through our Discord server for more info!",
        )

    def notify_unrestricted(self) -> None:
        """
        Send FokaBot message to alert the user that he has been unrestricted
        and he has to log in again.

        :return:
        """
        chat.sendMessage(
            glob.BOT_NAME,
            self.username,
            "Your account has been unrestricted! Please re-log to refresh your status.",
        )

    def joinStream(self, name: str) -> None:
        """
        Join a packet stream, or create it if the stream doesn't exist.

        :param name: stream name
        :return:
        """
        glob.streams.join(name, token=self.token)
        if name not in self.streams:
            self.streams.append(name)

    def leaveStream(self, name: str) -> None:
        """
        Leave a packets stream

        :param name: stream name
        :return:
        """
        glob.streams.leave(name, token=self.token)
        if name in self.streams:
            self.streams.remove(name)

    def leaveAllStreams(self) -> None:
        """
        Leave all joined packet streams

        :return:
        """
        for i in self.streams:
            self.leaveStream(i)

    def awayCheck(self, userID: int) -> bool:
        """
        Returns True if userID doesn't know that we are away
        Returns False if we are not away or if userID already knows we are away

        :param userID: original sender userID
        :return:
        """
        if self.awayMessage == "" or userID in self.sentAway:
            return False
        self.sentAway.append(userID)
        return True

    def addMessageInBuffer(self, chan: str, message: str):
        """
        Add a message in messages buffer (10 messages, truncated at 50 chars).
        Used as proof when the user gets reported.

        :param chan: channel
        :param message: message content
        :return:
        """
        if len(self.messagesBuffer) > 9:
            self.messagesBuffer = self.messagesBuffer[1:]
        self.messagesBuffer.append(
            "{time} - {user}@{channel}: {message}".format(
                time=time.strftime("%H:%M", time.localtime()),
                user=self.username,
                channel=chan,
                message=message[:50],
            ),
        )

    def getMessagesBufferString(self) -> str:
        """
        Get the content of the messages buffer as a string

        :return: messages buffer content as a string
        """
        return "\n".join(x for x in self.messagesBuffer)
