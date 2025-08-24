from __future__ import annotations

import copy
import json
import threading
import time
from typing import Optional
from typing import TYPE_CHECKING

import settings
from constants import dataTypes
from constants import matchModModes
from constants import matchScoringTypes
from constants import matchTeams
from constants import matchTeamTypes
from constants import serverPackets
from constants import slotStatuses
from helpers import chatHelper as chat
from objects import glob
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from objects.osuToken import UserToken


class Slot:
    def __init__(self):
        self.status = slotStatuses.FREE
        self.team = matchTeams.NO_TEAM
        self.userID = -1
        self.user = None
        self.mods = 0
        self.loaded = False
        self.skip = False
        self.complete = False
        self.score = 0
        self.failed = False
        self.passed = True


class Match:
    def __init__(
        self,
        matchID: int,
        matchName: str,
        matchPassword: str,
        beatmapID: int,
        beatmapName: str,
        beatmapMD5: str,
        gameMode: int,
        hostUserID: int,
        isTourney=False,
    ):
        """
        Create a new match object

        :param matchID: match progressive identifier
        :param matchName: match name, string
        :param matchPassword: match md5 password. Leave empty for no password
        :param beatmapID: beatmap ID
        :param beatmapName: beatmap name, string
        :param beatmapMD5: beatmap md5 hash, string
        :param gameMode: game mode ID. See gameModes.py
        :param hostUserID: user id of the host
        """
        self.matchID = matchID
        self.streamName = f"multi/{self.matchID}"
        self.playingStreamName = f"{self.streamName}/playing"
        self.inProgress = False
        self.mods = 0
        self.matchName = matchName
        self.matchPassword = matchPassword
        self.beatmapID = beatmapID
        self.beatmapName = beatmapName
        self.beatmapMD5 = beatmapMD5
        self.hostUserID = hostUserID
        self.gameMode = gameMode
        self.matchScoringType = matchScoringTypes.SCORE  # default values
        self.matchTeamType = matchTeamTypes.HEAD_TO_HEAD  # default value
        self.matchModMode = matchModModes.NORMAL  # default value
        self.seed = 0
        self.matchDataCache = b""
        self.isTourney = isTourney
        self.isLocked = (
            False  # if True, users can't change slots/teams. Used in tourney matches
        )
        self.isStarting = False
        self._lock = threading.Lock()
        self.createTime = int(time.time())
        self.vinseID = None
        self.bloodcatAlert = False

        self.pp_competition = False

        # Create all slots and reset them
        self.slots: list[Slot] = []
        for _ in range(16):
            self.slots.append(Slot())

        # Create streams
        glob.streams.add(self.streamName)
        glob.streams.add(self.playingStreamName)

        # Create #multiplayer channel
        glob.channels.addHiddenChannel(f"#multi_{self.matchID}")
        logger.info(
            "MPROOM{}: {} match created!".format(
                self.matchID,
                "Tourney" if self.isTourney else "Normal",
            ),
        )

    def getMatchData(self, censored=False) -> bytes:
        """
        Return binary match data structure for packetHelper
        Return binary match data structure for packetHelper

        :return:
        """
        # General match info
        # TODO: Test without safe copy, the error might have been caused by outdated python bytecode cache
        # safeMatch = copy.deepcopy(self)
        struct = [
            [self.matchID, dataTypes.UINT16],
            [int(self.inProgress), dataTypes.BYTE],
            [0, dataTypes.BYTE],
            [self.mods, dataTypes.UINT32],
            [self.matchName, dataTypes.STRING],
        ]
        if censored and self.matchPassword:
            struct.append(["RealistikDash was here.", dataTypes.STRING])
        else:
            struct.append([self.matchPassword, dataTypes.STRING])

        struct.extend(
            [
                [self.beatmapName, dataTypes.STRING],
                [self.beatmapID, dataTypes.UINT32],
                [self.beatmapMD5, dataTypes.STRING],
            ],
        )

        # Slots status IDs, always 16 elements
        for i in range(0, 16):
            struct.append([self.slots[i].status, dataTypes.BYTE])

        # Slot teams, always 16 elements
        for i in range(0, 16):
            struct.append([self.slots[i].team, dataTypes.BYTE])

        # Slot user ID. Write only if slot is occupied
        for i in range(0, 16):
            if (
                self.slots[i].user is not None
                and self.slots[i].user in glob.tokens.tokens
            ):
                struct.append(
                    [glob.tokens.tokens[self.slots[i].user].userID, dataTypes.UINT32],
                )

        # Other match data
        struct.extend(
            [
                [self.hostUserID, dataTypes.SINT32],
                [self.gameMode, dataTypes.BYTE],
                [self.matchScoringType, dataTypes.BYTE],
                [self.matchTeamType, dataTypes.BYTE],
                [self.matchModMode, dataTypes.BYTE],
            ],
        )

        # Slot mods if free mod is enabled
        if self.matchModMode == matchModModes.FREE_MOD:
            for i in range(0, 16):
                struct.append([self.slots[i].mods, dataTypes.UINT32])

        # Seed idk
        # TODO: Implement this, it should be used for mania "random" mod
        struct.append([self.seed, dataTypes.UINT32])

        return struct

    def setHost(self, newHost: int) -> bool:
        """
        Set room host to newHost and send him host packet

        :param newHost: new host userID
        :return:
        """
        slotID = self.getUserSlotID(newHost)
        if slotID is None or self.slots[slotID].user not in glob.tokens.tokens:
            return False
        token = glob.tokens.tokens[self.slots[slotID].user]
        self.hostUserID = newHost
        token.enqueue(serverPackets.match_new_host_notify())
        self.sendUpdates()
        logger.info(
            "User is now match host",
            extra={"match_id": self.matchID, "username": token.username},
        )
        return True

    def removeHost(self) -> None:
        """
        Removes the host (for tourney matches)
        :return:
        """
        self.hostUserID = -1
        self.sendUpdates()
        logger.info("Match host removed", extra={"match_id": self.matchID})

    # TODO: This is aids. rewrite.
    def setSlot(
        self,
        slotID,
        status=None,
        team=None,
        user="",
        mods=None,
        loaded=None,
        skip=None,
        complete=None,
    ):
        """
        Set data for a specific slot.
        All fields but slotID are optional.
        Skipped fields won't be edited.

        :param slotID: slot ID
        :param status: new status
        :param team: new team
        :param user: new user id
        :param mods: new mods
        :param loaded: new loaded status
        :param skip: new skip value
        :param complete: new completed value
        :return:
        """
        if status is not None:
            self.slots[slotID].status = status

        if team is not None:
            self.slots[slotID].team = team

        if user != "":
            self.slots[slotID].user = user

        if mods is not None:
            self.slots[slotID].mods = mods

        if loaded is not None:
            self.slots[slotID].loaded = loaded

        if skip is not None:
            self.slots[slotID].skip = skip

        if complete is not None:
            self.slots[slotID].complete = complete

    def setSlotMods(self, slotID: int, mods: int) -> None:
        """
        Set slotID mods. Same as calling setSlot and then sendUpdate

        :param slotID: slot number
        :param mods: new mods
        :return:
        """
        # Set new slot data and send update
        self.setSlot(slotID, mods=mods)
        self.sendUpdates()
        logger.info(
            f"MPROOM{self.matchID}: Slot{slotID} mods changed to {mods}",
        )

    def toggleSlotReady(self, slotID: int) -> None:
        """
        Switch slotID ready/not ready status
        Same as calling setSlot and then sendUpdate

        :param slotID: slot number
        :return:
        """
        # Update ready status and setnd update
        if self.slots[slotID].user is None or self.isStarting:
            return
        oldStatus = self.slots[slotID].status
        if oldStatus == slotStatuses.READY:
            newStatus = slotStatuses.NOT_READY
        else:
            newStatus = slotStatuses.READY
        self.setSlot(slotID, newStatus)
        self.sendUpdates()
        logger.info(
            "MPROOM{}: Slot{} changed ready status to {}".format(
                self.matchID,
                slotID,
                self.slots[slotID].status,
            ),
        )

    def toggleSlotLocked(self, slotID: int) -> None:
        """
        Lock a slot
        Same as calling setSlot and then sendUpdate

        :param slotID: slot number
        :return:
        """
        # Check if slot is already locked
        if self.slots[slotID].status == slotStatuses.LOCKED:
            newStatus = slotStatuses.FREE
        else:
            newStatus = slotStatuses.LOCKED

        # Send updated settings to kicked user, so THEY!!! (WTF RIPPLE??) returns to lobby
        if (
            self.slots[slotID].user is not None
            and self.slots[slotID].user in glob.tokens.tokens
        ):
            glob.tokens.tokens[self.slots[slotID].user].enqueue(
                serverPackets.match_update(self.matchID),
            )

        # Set new slot status
        self.setSlot(slotID, status=newStatus, team=0, user=None, mods=0)

        # Send updates to everyone else
        self.sendUpdates()
        logger.info(
            "MPROOM{}: Slot{} {}".format(
                self.matchID,
                slotID,
                "locked" if newStatus == slotStatuses.LOCKED else "unlocked",
            ),
        )

    def playerLoaded(self, userID: int) -> None:
        """
        Set a player loaded status to True

        :param userID: ID of user
        :return:
        """
        slotID = self.getUserSlotID(userID)
        if slotID is None:
            return

        # Set loaded to True
        self.slots[slotID].loaded = True
        logger.info(
            "User loaded in match",
            extra={"match_id": self.matchID, "user_id": userID},
        )

        # Check all loaded
        total = 0
        loaded = 0
        for i in range(0, 16):
            if self.slots[i].status == slotStatuses.PLAYING:
                total += 1
                if self.slots[i].loaded:
                    loaded += 1

        if total == loaded:
            self.allPlayersLoaded()

    def allPlayersLoaded(self) -> None:
        """
        Send allPlayersLoaded packet to every playing usr in match

        :return:
        """
        glob.streams.broadcast(
            self.playingStreamName,
            serverPackets.match_all_players_loaded(),
        )
        logger.info(
            "All players loaded - match starting",
            extra={"match_id": self.matchID},
        )

    def playerSkip(self, userID: int) -> None:
        """
        Set a player skip status to True

        :param userID: ID of user
        :return:
        """
        slotID = self.getUserSlotID(userID)
        if slotID is None:
            return

        # Set skip to True
        self.slots[slotID].skip = True
        logger.info(
            "User skipped in match",
            extra={"match_id": self.matchID, "user_id": userID},
        )

        # Send skip packet to every playing user
        # glob.streams.broadcast(self.playingStreamName, serverPackets.match_player_skipped(glob.tokens.tokens[self.slots[slotID].user].userID))
        glob.streams.broadcast(
            self.playingStreamName,
            serverPackets.match_player_skipped(slotID),
        )

        # Check all skipped
        total = 0
        skipped = 0
        for i in range(0, 16):
            if self.slots[i].status == slotStatuses.PLAYING:
                total += 1
                if self.slots[i].skip:
                    skipped += 1

        if total == skipped:
            self.allPlayersSkipped()

    def allPlayersSkipped(self) -> None:
        """
        Send allPlayersSkipped packet to every playing usr in match

        :return:
        """
        glob.streams.broadcast(
            self.playingStreamName,
            serverPackets.match_all_skipped(),
        )
        logger.info("All players skipped in match", extra={"match_id": self.matchID})

    def updateScore(self, slotID: int, score: int) -> None:
        """
        Update score for a slot

        :param slotID: the slot that the user that is updating their score is in
        :param score: the new score to update
        :return:
        """
        self.slots[slotID].score = score

    def updateHP(self, slotID: int, hp: int) -> None:
        """
        Update HP for a slot

        :param slotID: the slot that the user that is updating their hp is in
        :param hp: the new hp to update
        :return:
        """
        self.slots[slotID].failed = True if hp == 254 else False

    def playerCompleted(self, userID: int) -> None:
        """
        Set userID's slot completed to True

        :param userID: ID of user
        """
        slotID = self.getUserSlotID(userID)
        if slotID is None:
            return
        self.setSlot(slotID, complete=True)

        # Console output
        logger.info(
            f"MPROOM{self.matchID}: User {userID} has completed his play",
        )

        # Check all completed
        total = 0
        completed = 0
        for i in range(0, 16):
            if self.slots[i].status == slotStatuses.PLAYING:
                total += 1
                if self.slots[i].complete:
                    completed += 1

        if total == completed:
            self.allPlayersCompleted()

    def allPlayersCompleted(self) -> None:
        """
        Cleanup match stuff and send match end packet to everyone

        :return:
        """
        # Collect some info about the match that just ended to send to the api
        infoToSend = {
            "id": self.matchID,
            "name": self.matchName,
            "beatmap_id": self.beatmapID,
            "mods": self.mods,
            "game_mode": self.gameMode,
            "scores": {},
        }

        # Add score info for each player
        for i in range(0, 16):
            if (
                self.slots[i].user is not None
                and self.slots[i].status == slotStatuses.PLAYING
            ):
                infoToSend["scores"][glob.tokens.tokens[self.slots[i].user].userID] = {
                    "score": self.slots[i].score,
                    "mods": self.slots[i].mods,
                    "failed": self.slots[i].failed,
                    "pass": self.slots[i].passed,
                    "team": self.slots[i].team,
                }

        # Send the info to the api
        glob.redis.publish("api:mp_complete_match", json.dumps(infoToSend))

        # Reset inProgress
        self.inProgress = False

        # Reset slots
        self.resetSlots()

        # Send match update
        self.sendUpdates()

        # Send match complete
        glob.streams.broadcast(self.streamName, serverPackets.match_complete())

        # Destroy playing stream
        glob.streams.dispose(self.playingStreamName)
        glob.streams.remove(self.playingStreamName)

        # Console output
        logger.info("Match completed", extra={"match_id": self.matchID})

        # Set vinse id if needed
        chanName = f"#multi_{self.matchID}"
        # Changing this to be a general notice.
        if not self.bloodcatAlert:
            chat.sendMessage(
                glob.BOT_NAME,
                chanName,
                f"Hey! Welcome to the {settings.PS_NAME} multiplayer! If you ever encounter "
                "a map you are unable to download through our direct, you can use the "
                "!mirror command to get an external download link!",
            )
            self.bloodcatAlert = True

        # If this is a tournament match, then we send a notification in the chat
        # saying that the match has completed.
        if self.isTourney and (chanName in glob.channels.channels):
            chat.sendMessage(glob.BOT_NAME, chanName, "Match has just finished.")

    def resetSlots(self) -> None:
        for i in range(0, 16):
            if (
                self.slots[i].user is not None
                and self.slots[i].status == slotStatuses.PLAYING
            ):
                self.slots[i].status = slotStatuses.NOT_READY
                self.slots[i].loaded = False
                self.slots[i].skip = False
                self.slots[i].complete = False
                self.slots[i].score = 0
                self.slots[i].failed = False
                self.slots[i].passed = True

    def getUserSlotID(self, userID: int) -> Optional[int]:
        """
        Get slot ID occupied by userID

        :return: slot id if found, None if user is not in room
        """
        for i in range(0, 16):
            if (
                self.slots[i].user is not None
                and self.slots[i].user in glob.tokens.tokens
                and glob.tokens.tokens[self.slots[i].user].userID == userID
            ):
                return i
        return None

    def userJoin(self, user: UserToken):
        """
        Add someone to users in match

        :param user: user object of the user
        :return: True if join success, False if fail (room is full)
        """
        # Make sure we're not in this match
        for i in range(0, 16):
            if self.slots[i].user == user.token:
                # Set bugged slot to free
                self.setSlot(i, slotStatuses.FREE, 0, None, 0)

        # Find first free slot
        for i in range(0, 16):
            if self.slots[i].status == slotStatuses.FREE:
                # Occupy slot
                team = matchTeams.NO_TEAM
                if (
                    self.matchTeamType == matchTeamTypes.TEAM_VS
                    or self.matchTeamType == matchTeamTypes.TAG_TEAM_VS
                ):
                    team = matchTeams.RED if i % 2 == 0 else matchTeams.BLUE
                self.setSlot(i, slotStatuses.NOT_READY, team, user.token, 0)

                # Send updated match data
                self.sendUpdates()

                # Auto-join user to channel
                user.joinChannel(glob.channels.channels[f"#multi_{self.matchID}"])

                # Console output
                logger.info(
                    f"MPROOM{self.matchID}: {user.username} joined the room",
                )
                return True

        return False

    def userLeft(self, user: UserToken, disposeMatch=True):
        """
        Remove someone from users in match

        :param user: user object of the user
        :param disposeMatch: if `True`, will try to dispose match if there are no users in the room
        :return:
        """
        # Make sure the user is in room
        slotID = self.getUserSlotID(user.userID)
        if slotID is None:
            return

        # Set that slot to free
        self.setSlot(slotID, slotStatuses.FREE, 0, None, 0)

        # Check if everyone left
        if self.countUsers() == 0 and disposeMatch and not self.isTourney:
            # Dispose match
            glob.matches.match_dispose(self.matchID)
            logger.info(
                f"MPROOM{self.matchID}: Room disposed because all users left",
            )
            return

        # Check if host left
        if user.userID == self.hostUserID:
            # Give host to someone else
            for i in range(0, 16):
                if (
                    self.slots[i].user is not None
                    and self.slots[i].user in glob.tokens.tokens
                ):
                    self.setHost(glob.tokens.tokens[self.slots[i].user].userID)
                    break

        # Send updated match data
        self.sendUpdates()

        # Console output
        logger.info(
            "User left match room",
            extra={"match_id": self.matchID, "username": user.username},
        )

    def userChangeSlot(self, userID: int, newSlotID: int) -> bool:
        """
        Change userID slot to newSlotID

        :param userID: user that changed slot
        :param newSlotID: slot id of new slot
        :return:
        """
        # Make sure the match is not locked
        if self.isLocked or self.isStarting:
            return False

        # Make sure the user is in room
        oldSlotID = self.getUserSlotID(userID)
        if oldSlotID is None:
            return False

        # Make sure there is no one inside new slot
        if (
            self.slots[newSlotID].user is not None
            or self.slots[newSlotID].status != slotStatuses.FREE
        ):
            return False

        # Get old slot data
        oldData = copy.deepcopy(self.slots[oldSlotID])

        # Free old slot
        self.setSlot(oldSlotID, slotStatuses.FREE, 0, None, 0, False, False, False)

        # Occupy new slot
        self.setSlot(
            newSlotID,
            oldData.status,
            oldData.team,
            oldData.user,
            oldData.mods,
        )

        # Send updated match data
        self.sendUpdates()

        # Console output
        logger.info(
            f"MPROOM{self.matchID}: {userID} moved to slot {newSlotID}",
        )
        return True

    def changePassword(self, newPassword: str) -> None:
        """
        Change match password to newPassword

        :param newPassword: new password string
        :return:
        """
        self.matchPassword = newPassword

        # Send password change to every user in match
        glob.streams.broadcast(
            self.streamName,
            serverPackets.match_change_password(self.matchPassword),
        )

        # Send new match settings too
        self.sendUpdates()

        # Console output
        logger.info(
            f"MPROOM{self.matchID}: Password changed to {self.matchPassword}",
        )

    def changeMods(self, mods: int) -> None:
        """
        Set match global mods

        :param mods: mods bitwise int thing
        :return:
        """
        # Set new mods and send update
        self.mods = mods
        self.sendUpdates()
        logger.info(
            "Match mods changed",
            extra={"match_id": self.matchID, "mods": self.mods},
        )

    def userHasBeatmap(self, userID: int, has: bool = True):
        """
        Set no beatmap status for userID

        :param userID: ID of user
        :param has: True if has beatmap, false if not
        :return:
        """
        # Make sure the user is in room
        slotID = self.getUserSlotID(userID)
        if slotID is None:
            return

        # Set slot
        self.setSlot(slotID, slotStatuses.NO_MAP if not has else slotStatuses.NOT_READY)

        # Send updates
        self.sendUpdates()

    def transferHost(self, slotID: int):
        """
        Transfer host to slotID

        :param slotID: ID of slot
        :return:
        """
        # Make sure there is someone in that slot
        if (
            self.slots[slotID].user is None
            or self.slots[slotID].user not in glob.tokens.tokens
        ):
            return

        # Transfer host
        self.setHost(glob.tokens.tokens[self.slots[slotID].user].userID)

        # Send updates
        # self.sendUpdates()

    def playerFailed(self, userID: int):
        """
        Send userID's failed packet to everyone in match

        :param userID: ID of user
        :return:
        """
        # Make sure the user is in room
        slotID = self.getUserSlotID(userID)
        if slotID is None:
            return

        self.slots[slotID].passed = False

        # Send packet to everyone
        glob.streams.broadcast(
            self.playingStreamName,
            serverPackets.match_player_fail(slotID),
        )

        # Console output
        logger.info(
            "User failed in match",
            extra={"match_id": self.matchID, "user_id": userID},
        )

    def invite(self, fro: int, to: int):
        """
        Fro invites to in this match.

        :param fro: sender userID
        :param to: receiver userID
        :return:
        """
        # Get tokens
        froToken = glob.tokens.getTokenFromUserID(fro)
        toToken = glob.tokens.getTokenFromUserID(to)
        if froToken is None or toToken is None:
            return

        # BOT IS BUSY!!!
        if to == settings.PS_BOT_USER_ID:
            chat.sendMessage(
                glob.BOT_NAME,
                froToken.username,
                "I would love to join your match, but I'm busy keeping the server up and running. Sorry. Beep Boop.",
            )

        # Send message
        message = 'Come join my multiplayer match: "[osump://{}/{} {}]"'.format(
            self.matchID,
            self.matchPassword.replace(" ", "_"),
            self.matchName,
        )
        chat.sendMessage(token=froToken, to=toToken.username, message=message)

    def countUsers(self):
        """
        Return how many players are in that match

        :return: number of users
        """
        c = 0
        for i in range(0, 16):
            if self.slots[i].user is not None:
                c += 1
        return c

    def changeTeam(self, userID, newTeam=None):
        """
        Change userID's team

        :param userID: id of user
        :return:
        """
        # Make sure this match's mode has teams
        if (
            self.matchTeamType != matchTeamTypes.TEAM_VS
            and self.matchTeamType != matchTeamTypes.TAG_TEAM_VS
        ):
            return

        # Make sure the match is not locked
        if self.isLocked or self.isStarting:
            return

        # Make sure the user is in room
        slotID = self.getUserSlotID(userID)
        if slotID is None:
            return

        # Update slot and send update
        if newTeam is None:
            newTeam = (
                matchTeams.BLUE
                if self.slots[slotID].team == matchTeams.RED
                else matchTeams.RED
            )
        self.setSlot(slotID, None, newTeam)
        self.sendUpdates()

    def sendUpdates(self):
        """
        Send match updates packet to everyone in lobby and room streams

        :return:
        """
        self.matchDataCache = serverPackets.match_update(self.matchID)
        censoredDataCache = serverPackets.match_update(self.matchID, censored=True)
        if self.matchDataCache is not None:
            glob.streams.broadcast(self.streamName, self.matchDataCache)
        if censoredDataCache is not None:
            glob.streams.broadcast("lobby", censoredDataCache)
        else:
            logger.error(
                "MPROOM{}: Can't send match update packet, match data is None!!!".format(
                    self.matchID,
                ),
            )

    def checkTeams(self):
        """
        Check if match teams are valid

        :return: True if valid, False if invalid
        :return:
        """
        if (
            self.matchTeamType != matchTeamTypes.TEAM_VS
            and self.matchTeamType != matchTeamTypes.TAG_TEAM_VS
        ):
            # Teams are always valid if we have no teams
            return True

        # We have teams, check if they are valid
        firstTeam = -1
        for i in range(0, 16):
            if (
                self.slots[i].user is not None
                and (self.slots[i].status & slotStatuses.NO_MAP) == 0
            ):
                if firstTeam == -1:
                    firstTeam = self.slots[i].team
                elif firstTeam != self.slots[i].team:
                    logger.info(
                        "Match teams are valid",
                        extra={"match_id": self.matchID},
                    )
                    return True

        logger.warning("Match teams are invalid", extra={"match_id": self.matchID})
        return False

    def start(self):
        """
        Start the match

        :return:
        """
        # Remove isStarting timer flag thingie
        self.isStarting = False

        # Create playing channel
        glob.streams.add(self.playingStreamName)

        # Change inProgress value
        self.inProgress = True

        # Set playing to ready players and set load, skip and complete to False
        # Make clients join playing stream
        for i in range(0, 16):
            if self.slots[i].user in glob.tokens.tokens:
                self.slots[i].status = slotStatuses.PLAYING
                self.slots[i].loaded = False
                self.slots[i].skip = False
                self.slots[i].complete = False
                glob.tokens.tokens[self.slots[i].user].joinStream(
                    self.playingStreamName,
                )

        # Send match start packet
        glob.streams.broadcast(
            self.playingStreamName,
            serverPackets.match_start(self.matchID),
        )

        # Send updates
        self.sendUpdates()
        return True

    def forceSize(self, matchSize):
        for i in range(0, matchSize):
            if self.slots[i].status == slotStatuses.LOCKED:
                self.toggleSlotLocked(i)
        for i in range(matchSize, 16):
            if self.slots[i].status != slotStatuses.LOCKED:
                self.toggleSlotLocked(i)

    def abort(self):
        if not self.inProgress:
            logger.warning("Match is not in progress", extra={"match_id": self.matchID})
            return
        self.inProgress = False
        self.isStarting = False
        self.resetSlots()
        self.sendUpdates()
        glob.streams.broadcast(self.playingStreamName, serverPackets.match_abort())
        glob.streams.dispose(self.playingStreamName)
        glob.streams.remove(self.playingStreamName)
        logger.info("Match aborted", extra={"match_id": self.matchID})

    def initializeTeams(self):
        if (
            self.matchTeamType == matchTeamTypes.TEAM_VS
            or self.matchTeamType == matchTeamTypes.TAG_TEAM_VS
        ):
            # Set teams
            for i, _slot in enumerate(self.slots):
                _slot.team = matchTeams.RED if i % 2 == 0 else matchTeams.BLUE
        else:
            # Reset teams
            for _slot in self.slots:
                _slot.team = matchTeams.NO_TEAM

    def resetMods(self):
        for _slot in self.slots:
            _slot.mods = 0

    def resetReady(self):
        for _slot in self.slots:
            if _slot.status == slotStatuses.READY:
                _slot.status = slotStatuses.NOT_READY

    def sendReadyStatus(self):
        chanName = f"#multi_{self.matchID}"

        # Make sure match exists before attempting to do anything else
        if chanName not in glob.channels.channels:
            return

        totalUsers = 0
        readyUsers = 0

        for slot in self.slots:
            # Make sure there is a user in this slot
            if slot.user is None:
                continue

            # In this slot there is a user, so we increase the amount of total users
            # in this multi room.
            totalUsers += 1

            if slot.status == slotStatuses.READY:
                readyUsers += 1

        message = f"{readyUsers} users ready out of {totalUsers}."

        if totalUsers == readyUsers:
            message += " All users ready!"

        # Check whether there is anyone left in this match.
        if totalUsers == 0:
            message = "The match is now empty."

        chat.sendMessage(glob.BOT_NAME, chanName, message)

    def __enter__(self):
        # 🌚🌚🌚🌚🌚
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()
