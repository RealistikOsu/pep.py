from __future__ import annotations

import random

from common import generalUtils
from constants import clientPackets
from constants import matchModModes
from constants import matchTeams
from constants import matchTeamTypes
from constants import slotStatuses
from logger import log
from objects import glob


def handle(userToken, packetData):
    # Read new settings
    packetData = clientPackets.changeMatchSettings(packetData)

    # Get match ID
    matchID = userToken.matchID

    # Make sure the match exists
    if matchID not in glob.matches.matches:
        return

    # Host check
    with glob.matches.matches[matchID] as match:
        if userToken.userID != match.hostUserID:
            return

        # Realistik was her
        memeTitles = [
            "I hate boxes",
            "this text is funny",
            "Hit kids not juul",
            "dark is the best osu! player",
            "I'm spiderman",
            "DING DONG",
            "matt from wii sports",
            "Intel is an expensive space heater brand",
            "she so shiny",
            "im a freaking ferrari",
            "Welp shouldnt have bought that switch then",
            "RealistikBot hot",
        ]

        # Set match name
        match.matchName = (
            packetData["matchName"]
            if packetData["matchName"] != "meme"
            else random.choice(memeTitles)
        )

        # Update match settings
        match.inProgress = packetData["inProgress"]
        match.matchPassword = packetData["matchPassword"]
        match.beatmapName = packetData["beatmapName"]
        match.beatmapID = packetData["beatmapID"]
        match.hostUserID = packetData["hostUserID"]
        match.gameMode = packetData["gameMode"]

        oldBeatmapMD5 = match.beatmapMD5
        oldMods = match.mods
        oldMatchTeamType = match.matchTeamType

        match.mods = packetData["mods"]
        match.beatmapMD5 = packetData["beatmapMD5"]
        match.matchScoringType = packetData["scoringType"]
        match.matchTeamType = packetData["teamType"]
        match.matchModMode = packetData["freeMods"]

        # Reset ready if needed
        if oldMods != match.mods or oldBeatmapMD5 != match.beatmapMD5:
            match.resetReady()

        # Reset mods if needed
        if match.matchModMode == matchModModes.NORMAL:
            # Reset slot mods if not freeMods
            match.resetMods()
        else:
            # Reset match mods if freemod
            match.mods = 0

        # Initialize teams if team type changed
        if match.matchTeamType != oldMatchTeamType:
            match.initializeTeams()

        # Force no freemods if tag coop
        if (
            match.matchTeamType == matchTeamTypes.TAG_COOP
            or match.matchTeamType == matchTeamTypes.TAG_TEAM_VS
        ):
            match.matchModMode = matchModModes.NORMAL

        # Send updated settings
        match.sendUpdates()

        # Console output
        log.info(f"MPROOM{match.matchID}: Updated room settings")
