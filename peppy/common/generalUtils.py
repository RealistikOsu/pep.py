from __future__ import annotations

import hashlib
import random
import string
from functools import partial
from time import localtime
from time import strftime

from common.constants import mods
from logger import log


def randomString(length=8):
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(length)
    )


def stringToBool(s):
    """
    Convert a string (True/true/1) to bool

    :param s: string/int value
    :return: True/False
    """
    return s == "True" or s == "true" or s == "1" or s == 1


def fileMd5(filename):
    """
    Return filename's md5

    :param filename: name of the file
    :return: file md5
    """
    with open(filename, mode="rb") as f:
        d = hashlib.md5()
        for buf in iter(partial(f.read, 128), b""):
            d.update(buf)
    return d.hexdigest()


def stringMd5(s):
    """
    Return string's md5

    :param s: input string
    :return: `string`'s md5
    """
    d = hashlib.md5()
    d.update(s.encode("utf-8"))
    return d.hexdigest()


def getRank(
    gameMode=None,
    __mods=None,
    acc=None,
    c300=None,
    c100=None,
    c50=None,
    cmiss=None,
    *,
    score_=None,
):
    """
    Return a string with rank/grade for a given score.
    Used mainly for tillerino

    :param gameMode: game mode number
    :param __mods: mods value
    :param acc: accuracy
    :param c300: 300 hit count
    :param c100: 100 hit count
    :param c50: 50 hit count
    :param cmiss: misses count
    :param score_: score object. Optional.
    :return: rank/grade string
    """
    if score_ is not None:
        return getRank(
            score_.gameMode,
            score_.mods,
            score_.accuracy,
            score_.c300,
            score_.c100,
            score_.c50,
            score_.cMiss,
        )
    total = c300 + c100 + c50 + cmiss
    hdfl = (__mods & mods.HIDDEN > 0) or (__mods & mods.FLASHLIGHT > 0)

    def ss():
        return "XH" if hdfl else "X"

    def s():
        return "SH" if hdfl else "S"

    if gameMode == 0:
        # osu!std
        if acc == 100:
            return ss()
        if c300 / total > 0.90 and c50 / total < 0.1 and cmiss == 0:
            return s()
        if (c300 / total > 0.80 and cmiss == 0) or (c300 / total > 0.90):
            return "A"
        if (c300 / total > 0.70 and cmiss == 0) or (c300 / total > 0.80):
            return "B"
        if c300 / total > 0.60:
            return "C"
        return "D"
    elif gameMode == 1:
        # TODO: taiko rank
        return "A"
    elif gameMode == 2:
        # CtB
        if acc == 100:
            return ss()
        if 98.01 <= acc <= 99.99:
            return s()
        if 94.01 <= acc <= 98.00:
            return "A"
        if 90.01 <= acc <= 94.00:
            return "B"
        if 98.01 <= acc <= 90.00:
            return "C"
        return "D"
    elif gameMode == 3:
        # osu!mania
        if acc == 100:
            return ss()
        if acc > 95:
            return s()
        if acc > 90:
            return "A"
        if acc > 80:
            return "B"
        if acc > 70:
            return "C"
        return "D"

    return "A"


def getTimestamp():
    """
    Return current time in YYYY-MM-DD HH:MM:SS format.
    Used in logs.

    :return: readable timestamp
    """
    return strftime("%Y-%m-%d %H:%M:%S", localtime())


def hexString(s):
    """
    Output `s`'s bytes in DEX
    :param s: string
    :return: string with HEX values
    """
    return ":".join(f"{ord(str(c)):02x}" for c in s)


def readableMods(__mods):
    # TODO: same as common.scoreUtils.readableMods. Remove this or the other one.
    r = ""
    if __mods == 0:
        return "NM"
    if __mods & mods.NOFAIL > 0:
        r += "NF"
    if __mods & mods.EASY > 0:
        r += "EZ"
    if __mods & mods.HIDDEN > 0:
        r += "HD"
    if __mods & mods.HARDROCK > 0:
        r += "HR"
    if __mods & mods.DOUBLETIME > 0:
        r += "DT"
    if __mods & mods.HALFTIME > 0:
        r += "HT"
    if __mods & mods.FLASHLIGHT > 0:
        r += "FL"
    if __mods & mods.SPUNOUT > 0:
        r += "SO"
    if __mods & mods.RELAX > 0:
        r += "RX"
    if __mods & mods.RELAX2 > 0:
        r += "AP"

    return r


def calc_acc(mode, n300, n100, n50, miss, katu, geki):

    if mode == 0:
        hits = n300 + n100 + n50 + miss

        if hits == 0:
            return 0.0
        else:
            return 100.0 * ((n50 * 50) + (n100 * 100) + (n300 * 300)) / (hits * 300.0)

    elif mode == 1:
        hits = n300 + n100 + miss

        if hits == 0:
            return 0.0
        else:
            return 100.0 * ((n100 * 0.5) + n300) / hits
    elif mode == 2:
        hits = n300 + n100 + n50 + katu + miss

        if hits == 0:
            return 0.0
        else:
            return 100.0 * (n300 + n100 + n50) / hits
    elif mode == 3:
        hits = n300 + n100 + n50 + geki + katu + miss

        if hits == 0:
            return 0.0
        else:
            return (
                100.0
                * ((n50 * 50) + (n100 * 100) + (katu * 200.0) + ((n300 + geki) * 300.0))
                / (hits * 300.0)
            )

    raise ValueError(f"Invalid mode: {mode}")
