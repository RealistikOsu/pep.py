from __future__ import annotations

from common.constants import mods
from objects import glob


def readableGameMode(gameMode):
    """
    Convert numeric gameMode to a readable format. Can be used for db too.

    :param gameMode:
    :return:
    """
    # TODO: Same as common.constants.gameModes.getGameModeForDB, remove one
    if gameMode == 0:
        return "std"
    elif gameMode == 1:
        return "taiko"
    elif gameMode == 2:
        return "ctb"
    else:
        return "mania"


def readableMods(m):
    """
    Return a string with readable std mods.
    Used to convert a mods number for oppai

    :param m: mods bitwise number
    :return: readable mods string, eg HDDT
    """
    r = ""
    if m == 0:
        return "nomod"
    if m & mods.NOFAIL > 0:
        r += "NF"
    if m & mods.EASY > 0:
        r += "EZ"
    if m & mods.HIDDEN > 0:
        r += "HD"
    if m & mods.HARDROCK > 0:
        r += "HR"
    if m & mods.DOUBLETIME > 0:
        r += "DT"
    if m & mods.HALFTIME > 0:
        r += "HT"
    if m & mods.FLASHLIGHT > 0:
        r += "FL"
    if m & mods.SPUNOUT > 0:
        r += "SO"
    if m & mods.TOUCHSCREEN > 0:
        r += "TD"
    if m & mods.RELAX > 0:
        r += "RX"
    if m & mods.RELAX2 > 0:
        r += "AP"
    return r
