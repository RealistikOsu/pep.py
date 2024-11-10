from __future__ import annotations

import json
import time

import requests

try:
    from pymysql.err import ProgrammingError
except ImportError:
    from MySQLdb._exceptions import ProgrammingError

from typing import Optional

import settings
from common import generalUtils
from common.constants import gameModes, mods
from common.constants import privileges
from logger import log
from common.ripple import scoreUtils
from objects import glob


def getBeatmapTime(beatmapID):
    p = 0
    try:
        r = requests.get(
            f"https://bm6.aeris-dev.pw/api/cheesegull/b/{beatmapID}",
            timeout=2,
        ).text
        if r != "null\n":
            p = json.loads(r)["TotalLength"]
    except Exception:  # having backup mirror as having this fail literally kills the server
        log.warning("The default beatmap mirror doesnt work! Using a backup one.")
        r = requests.get(f"http://storage.ripple.moe/api/b/{beatmapID}", timeout=2).text
        if r != "null\n":
            p = json.loads(r)["TotalLength"]

    return p


def PPBoard(userID, relax):
    result = glob.db.fetch(
        "SELECT ppboard FROM {rx}_stats WHERE id = {userid}".format(
            rx="rx" if relax else "users",
            userid=userID,
        ),
    )
    return result["ppboard"]


def setPPBoard(userID, rx):
    glob.db.execute(
        "UPDATE {rx}_stats SET ppboard = 1 WHERE id = {userid}".format(
            rx="rx" if rx else "users",
            userid=userID,
        ),
    )


def setScoreBoard(userID, rx):
    glob.db.execute(
        "UPDATE {rx}_stats SET ppboard = 0 WHERE id = {userid}".format(
            rx="rx" if rx else "users",
            userid=userID,
        ),
    )


def noPPLimit(userID, relax):
    result = glob.db.fetch(
        "SELECT unrestricted_pp FROM {rx}_stats WHERE id = {userid}".format(
            rx="rx" if relax else "users",
            userid=userID,
        ),
    )
    return result["unrestricted_pp"]


def whitelistUserPPLimit(userID, rx):
    glob.db.execute(
        "UPDATE {rx}_stats SET unrestricted_pp = 1 WHERE id = {userid}".format(
            rx="rx" if rx else "users",
            userid=userID,
        ),
    )


# created ap variands
def PPBoardAP(userID):
    result = glob.db.fetch(
        f"SELECT ppboard FROM ap_stats WHERE id = {userID}",
    )
    return result["ppboard"]


def setPPBoardAP(userID):
    glob.db.execute(
        f"UPDATE ap_stats SET ppboard = 1 WHERE id = {userID}",
    )


def setScoreBoardAP(userID):
    glob.db.execute(
        f"UPDATE ap_stats SET ppboard = 0 WHERE id = {userID}",
    )


def noPPLimitAP(userID):
    result = glob.db.fetch(
        f"SELECT unrestricted_pp FROM ap_stats WHERE id = {userID}",
    )
    return result["unrestricted_pp"]


def whitelistUserPPLimitAP(userID):
    glob.db.execute(
        "UPDATE ap_stats SET unrestricted_pp = 1 WHERE id = {userid}".format(
            userid=userID,
        ),
    )


def incrementPlaytime(userID, gameMode=0, length=0):
    modeForDB = gameModes.getGameModeForDB(gameMode)
    result = glob.db.fetch(
        "SELECT playtime_{gm} as playtime FROM users_stats WHERE id = %s".format(
            gm=modeForDB,
        ),
        [userID],
    )
    if result is not None:
        glob.db.execute(
            "UPDATE users_stats SET playtime_{gm} = %s WHERE id = %s".format(
                gm=modeForDB,
            ),
            [(int(result["playtime"]) + int(length)), userID],
        )
    else:
        print("Something went wrong...")


def incrementPlaytimeRX(userID, gameMode=0, length=0):
    modeForDB = gameModes.getGameModeForDB(gameMode)
    result = glob.db.fetch(
        "SELECT playtime_{gm} as playtime FROM rx_stats WHERE id = %s".format(
            gm=modeForDB,
        ),
        [userID],
    )
    if result is not None:
        glob.db.execute(
            f"UPDATE rx_stats SET playtime_{modeForDB} = %s WHERE id = %s",
            [(int(result["playtime"]) + int(length)), userID],
        )
    else:
        print("Something went wrong...")


def incrementPlaytimeAP(userID, gameMode=0, length=0):
    modeForDB = gameModes.getGameModeForDB(gameMode)
    result = glob.db.fetch(
        "SELECT playtime_{gm} as playtime FROM ap_stats WHERE id = %s".format(
            gm=modeForDB,
        ),
        [userID],
    )
    if result is not None:
        glob.db.execute(
            f"UPDATE ap_stats SET playtime_{modeForDB} = %s WHERE id = %s",
            [(int(result["playtime"]) + int(length)), userID],
        )
    else:
        print("Something went wrong...")


# rel was here
def getUserStats(userID, gameMode):
    """
    Get all user stats relative to `gameMode`

    :param userID:
    :param gameMode: game mode number
    :return: dictionary with result
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)

    # Get stats
    stats = glob.db.fetch(
        """SELECT
                        ranked_score_{gm} AS rankedScore,
                        avg_accuracy_{gm} AS accuracy,
                        playcount_{gm} AS playcount,
                        total_score_{gm} AS totalScore,
                        pp_{gm} AS pp
                        FROM users_stats WHERE id = %s LIMIT 1""".format(
            gm=modeForDB,
        ),
        [userID],
    )

    # Get game rank
    stats["gameRank"] = getGameRank(userID, gameMode)

    # Return stats + game rank
    return stats


def getUserStatsRx(userID, gameMode):
    """
    Get all user stats relative to `gameMode`

    :param userID:
    :param gameMode: game mode number
    :return: dictionary with result
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)

    # Get stats
    if gameMode == 3:
        stats = glob.db.fetch(
            """SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM users_stats WHERE id = %s LIMIT 1""".format(
                gm=modeForDB,
            ),
            [userID],
        )

    else:

        # Get stats
        stats = glob.db.fetch(
            """SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM rx_stats WHERE id = %s LIMIT 1""".format(
                gm=modeForDB,
            ),
            [userID],
        )

    # Get game rank
    stats["gameRank"] = getGameRankRx(userID, gameMode)

    # Return stats + game rank
    return stats


def getUserStatsAP(userID, gameMode):
    """
    Get all user stats relative to `gameMode`

    :param userID:
    :param gameMode: game mode number
    :return: dictionary with result
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)

    # Get stats
    if gameMode == 3:  # mania
        stats = glob.db.fetch(
            """SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM users_stats WHERE id = %s LIMIT 1""".format(
                gm=modeForDB,
            ),
            [userID],
        )

    else:

        # Get stats
        stats = glob.db.fetch(
            """SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM ap_stats WHERE id = %s LIMIT 1""".format(
                gm=modeForDB,
            ),
            [userID],
        )

    # Get game rank
    stats["gameRank"] = getGameRankAP(userID, gameMode)

    # Return stats + game rank
    return stats


def getMaxCombo(userID, gameMode):
    """
    Get all user stats relative to `gameMode`

    :param userID:
    :param gameMode: game mode number
    :return: dictionary with result
    """
    # Get stats
    maxcombo = glob.db.fetch(
        "SELECT max_combo FROM scores WHERE userid = %s AND play_mode = %s ORDER BY max_combo DESC LIMIT 1",
        [userID, gameMode],
    )

    # Return stats + game rank
    return maxcombo["max_combo"]


def getMaxComboRX(userID, gameMode):
    """
    Get all user stats relative to `gameMode`

    :param userID:
    :param gameMode: game mode number
    :return: dictionary with result
    """
    # Get stats
    maxcombo = glob.db.fetch(
        "SELECT max_combo FROM scores_relax WHERE userid = %s AND play_mode = %s ORDER BY max_combo DESC LIMIT 1",
        [userID, gameMode],
    )

    # Return stats + game rank
    return maxcombo["max_combo"]


def getMaxComboAP(userID, gameMode):
    """
    Get all user stats relative to `gameMode`

    :param userID:
    :param gameMode: game mode number
    :return: dictionary with result
    """
    # Get stats
    maxcombo = glob.db.fetch(
        "SELECT max_combo FROM scores_ap WHERE userid = %s AND play_mode = %s ORDER BY max_combo DESC LIMIT 1",
        [userID, gameMode],
    )

    # Return stats + game rank
    return maxcombo["max_combo"]


def getIDSafe(_safeUsername):
    """
    Get user ID from a safe username
    :param _safeUsername: safe username
    :return: None if the user doesn't exist, else user id
    """
    result = glob.db.fetch(
        "SELECT id FROM users WHERE username_safe = %s LIMIT 1",
        [_safeUsername],
    )
    if result is not None:
        return result["id"]
    return None


def getID(username):
    """
    Get username's user ID from userID redis cache (if cache hit)
    or from db (and cache it for other requests) if cache miss

    :param username: user
    :return: user id or 0 if user doesn't exist
    """
    # Get userID from redis
    usernameSafe = safeUsername(username)
    userID = glob.redis.get(f"ripple:userid_cache:{usernameSafe}")

    if userID is None:
        # If it's not in redis, get it from mysql
        userID = getIDSafe(usernameSafe)

        # If it's invalid, return 0
        if userID is None:
            return 0

        # Otherwise, save it in redis and return it
        glob.redis.set(
            f"ripple:userid_cache:{usernameSafe}",
            userID,
            3600,
        )  # expires in 1 hour
        return userID

    # Return userid from redis
    return int(userID)


def getUsername(userID):
    """
    Get userID's username

    :param userID: user id
    :return: username or None
    """
    result = glob.db.fetch("SELECT username FROM users WHERE id = %s LIMIT 1", [userID])
    if result is None:
        return None
    return result["username"]


def getSafeUsername(userID):
    """
    Get userID's safe username

    :param userID: user id
    :return: username or None
    """
    result = glob.db.fetch(
        "SELECT username_safe FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is None:
        return None
    return result["username_safe"]


def exists(userID):
    """
    Check if given userID exists

    :param userID: user id to check
    :return: True if the user exists, else False
    """
    return (
        True
        if glob.db.fetch("SELECT id FROM users WHERE id = %s LIMIT 1", [userID])
        is not None
        else False
    )


def getRequiredScoreForLevel(level):
    """
    Return score required to reach a level

    :param level: level to reach
    :return: required score
    """
    if level <= 100:
        if level >= 2:
            return 5000 / 3 * (4 * (level**3) - 3 * (level**2) - level) + 1.25 * (
                1.8 ** (level - 60)
            )
        elif level <= 0 or level == 1:
            return 1  # Should be 0, but we get division by 0 below so set to 1
    elif level >= 101:
        return 26931190829 + 100000000000 * (level - 100)


def getLevel(totalScore):
    """
    Return level from totalScore

    :param totalScore: total score
    :return: level
    """
    level = 1
    while True:
        # if the level is > 8000, it's probably an endless loop. terminate it.
        if level > 8000:
            return level

        # Calculate required score
        reqScore = getRequiredScoreForLevel(level)

        # Check if this is our level
        if totalScore <= reqScore:
            # Our level, return it and break
            return level - 1
        else:
            # Not our level, calculate score for next level
            level += 1


def updateLevel(userID, gameMode=0, totalScore=0):
    """
    Update level in DB for userID relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :param totalScore: new total score
    :return:
    """
    # Make sure the user exists
    # if not exists(userID):
    #     return

    # Get total score from db if not passed
    mode = scoreUtils.readableGameMode(gameMode)
    if totalScore == 0:
        totalScore = glob.db.fetch(
            "SELECT total_score_{m} as total_score FROM users_stats WHERE id = %s LIMIT 1".format(
                m=mode,
            ),
            [userID],
        )
        if totalScore:
            totalScore = totalScore["total_score"]

    # Calculate level from totalScore
    level = getLevel(totalScore)

    # Save new level
    glob.db.execute(
        f"UPDATE users_stats SET level_{mode} = %s WHERE id = %s LIMIT 1",
        [level, userID],
    )


def updateLevelRX(userID, gameMode=0, totalScore=0):
    """
    Update level in DB for userID relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :param totalScore: new total score
    :return:
    """
    # Make sure the user exists
    # if not exists(userID):
    #   return

    # Get total score from db if not passed
    mode = scoreUtils.readableGameMode(gameMode)
    if totalScore == 0:
        totalScore = glob.db.fetch(
            "SELECT total_score_{m} as total_score FROM rx_stats WHERE id = %s LIMIT 1".format(
                m=mode,
            ),
            [userID],
        )
        if totalScore:
            totalScore = totalScore["total_score"]

    # Calculate level from totalScore
    level = getLevel(totalScore)

    # Save new level
    glob.db.execute(
        f"UPDATE rx_stats SET level_{mode} = %s WHERE id = %s LIMIT 1",
        [level, userID],
    )


def updateLevelAP(userID, gameMode=0, totalScore=0):
    """
    Update level in DB for userID relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :param totalScore: new total score
    :return:
    """
    # Make sure the user exists
    # if not exists(userID):
    #   return

    # Get total score from db if not passed
    mode = scoreUtils.readableGameMode(gameMode)
    if totalScore == 0:
        totalScore = glob.db.fetch(
            "SELECT total_score_{m} as total_score FROM ap_stats WHERE id = %s LIMIT 1".format(
                m=mode,
            ),
            [userID],
        )
        if totalScore:
            totalScore = totalScore["total_score"]

    # Calculate level from totalScore
    level = getLevel(totalScore)

    # Save new level
    glob.db.execute(
        f"UPDATE ap_stats SET level_{mode} = %s WHERE id = %s LIMIT 1",
        [level, userID],
    )


def calculateAccuracy(userID, gameMode):
    """
    Calculate accuracy value for userID relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: new accuracy
    """
    # Get best accuracy scores
    bestAccScores = glob.db.fetchAll(
        "SELECT accuracy FROM scores WHERE userid = %s AND play_mode = %s AND completed = 3 ORDER BY pp DESC LIMIT 500",
        (userID, gameMode),
    )

    v = 0
    if bestAccScores is not None:
        # Calculate weighted accuracy
        totalAcc = 0
        divideTotal = 0
        k = 0
        for i in bestAccScores:
            add = int((0.95**k) * 100)
            totalAcc += i["accuracy"] * add
            divideTotal += add
            k += 1
        # echo "$add - $totalacc - $divideTotal\n"
        if divideTotal != 0:
            v = totalAcc / divideTotal
        else:
            v = 0
    return v


def calculateAccuracyRX(userID, gameMode):
    """
    Calculate accuracy value for userID relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: new accuracy
    """
    # Get best accuracy scores
    bestAccScores = glob.db.fetchAll(
        "SELECT accuracy FROM scores_relax WHERE userid = %s AND play_mode = %s AND completed = 3 ORDER BY pp DESC LIMIT 500",
        [userID, gameMode],
    )

    v = 0
    if bestAccScores is not None:
        # Calculate weighted accuracy
        totalAcc = 0
        divideTotal = 0
        k = 0
        for i in bestAccScores:
            add = int((0.95**k) * 100)
            totalAcc += i["accuracy"] * add
            divideTotal += add
            k += 1
        # echo "$add - $totalacc - $divideTotal\n"
        if divideTotal != 0:
            v = totalAcc / divideTotal
        else:
            v = 0
    return v


def calculateAccuracyAP(userID, gameMode):
    """
    Calculate accuracy value for userID relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: new accuracy
    """
    # Get best accuracy scores
    bestAccScores = glob.db.fetchAll(
        "SELECT accuracy FROM scores_ap WHERE userid = %s AND play_mode = %s AND completed = 3 ORDER BY pp DESC LIMIT 500",
        [userID, gameMode],
    )

    v = 0
    if bestAccScores is not None:
        # Calculate weighted accuracy
        totalAcc = 0
        divideTotal = 0
        k = 0
        for i in bestAccScores:
            add = int((0.95**k) * 100)
            totalAcc += i["accuracy"] * add
            divideTotal += add
            k += 1
        # echo "$add - $totalacc - $divideTotal\n"
        if divideTotal != 0:
            v = totalAcc / divideTotal
        else:
            v = 0
    return v


def calculatePP(userID, gameMode):
    """
    Calculate userID's total PP for gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: total PP
    """
    return sum(
        round(round(row["pp"]) * 0.95**i)
        for i, row in enumerate(
            glob.db.fetchAll(
                "SELECT pp FROM scores LEFT JOIN(beatmaps) USING(beatmap_md5) "
                "WHERE userid = %s AND play_mode = %s AND completed = 3 AND ranked >= 2 "
                "ORDER BY pp DESC LIMIT 500",
                (userID, gameMode),
            ),
        )
    )


def calculatePPRelax(userID, gameMode):
    """
    Calculate userID's total PP for gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: total PP
    """
    return sum(
        round(round(row["pp"]) * 0.95**i)
        for i, row in enumerate(
            glob.db.fetchAll(
                "SELECT pp FROM scores_relax LEFT JOIN(beatmaps) USING(beatmap_md5) "
                "WHERE userid = %s AND play_mode = %s AND completed = 3 AND ranked >= 2 "
                "ORDER BY pp DESC LIMIT 500",
                (userID, gameMode),
            ),
        )
    )


def calculatePPAP(userID, gameMode):  # ppap
    """
    Calculate userID's total PP for gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: total PP
    """
    return sum(
        round(round(row["pp"]) * 0.95**i)
        for i, row in enumerate(
            glob.db.fetchAll(
                "SELECT pp FROM scores_ap LEFT JOIN(beatmaps) USING(beatmap_md5) "
                "WHERE userid = %s AND play_mode = %s AND completed = 3 AND ranked >= 2 "
                "ORDER BY pp DESC LIMIT 500",
                (userID, gameMode),
            ),
        )
    )


def updateAccuracy(userID, gameMode):
    """
    Update accuracy value for userID relative to gameMode in DB

    :param userID: user id
    :param gameMode: gameMode number
    :return:
    """
    newAcc = calculateAccuracy(userID, gameMode)
    mode = scoreUtils.readableGameMode(gameMode)
    glob.db.execute(
        "UPDATE users_stats SET avg_accuracy_{m} = %s WHERE id = %s LIMIT 1".format(
            m=mode,
        ),
        [newAcc, userID],
    )


def updateAccuracyRX(userID, gameMode):
    """
    Update accuracy value for userID relative to gameMode in DB

    :param userID: user id
    :param gameMode: gameMode number
    :return:
    """
    newAcc = calculateAccuracyRX(userID, gameMode)
    mode = scoreUtils.readableGameMode(gameMode)
    glob.db.execute(
        "UPDATE rx_stats SET avg_accuracy_{m} = %s WHERE id = %s LIMIT 1".format(
            m=mode,
        ),
        [newAcc, userID],
    )


def updateAccuracyAP(userID, gameMode):
    """
    Update accuracy value for userID relative to gameMode in DB

    :param userID: user id
    :param gameMode: gameMode number
    :return:
    """
    newAcc = calculateAccuracyAP(userID, gameMode)
    mode = scoreUtils.readableGameMode(gameMode)
    glob.db.execute(
        "UPDATE ap_stats SET avg_accuracy_{m} = %s WHERE id = %s LIMIT 1".format(
            m=mode,
        ),
        [newAcc, userID],
    )


def updatePP(userID, gameMode):
    """
    Update userID's pp with new value

    :param userID: user id
    :param gameMode: game mode number
    """
    glob.db.execute(
        "UPDATE users_stats SET pp_{}=%s WHERE id = %s LIMIT 1".format(
            scoreUtils.readableGameMode(gameMode),
        ),
        (calculatePP(userID, gameMode), userID),
    )


def updatePPRelax(userID, gameMode):
    """
    Update userID's pp with new value

    :param userID: user id
    :param gameMode: game mode number
    """
    glob.db.execute(
        "UPDATE rx_stats SET pp_{}=%s WHERE id = %s LIMIT 1".format(
            scoreUtils.readableGameMode(gameMode),
        ),
        (calculatePPRelax(userID, gameMode), userID),
    )


def updatePPAP(userID, gameMode):
    """
    Update userID's pp with new value

    :param userID: user id
    :param gameMode: game mode number
    """
    glob.db.execute(
        "UPDATE ap_stats SET pp_{}=%s WHERE id = %s LIMIT 1".format(
            scoreUtils.readableGameMode(gameMode),
        ),
        (calculatePPAP(userID, gameMode), userID),
    )


def updateStats(userID, score_):
    """
    Update stats (playcount, total score, ranked score, level bla bla)
    with data relative to a score object

    :param userID:
    :param score_: score object
    :param beatmap_: beatmap object. Optional. If not passed, it'll be determined by score_.
    """

    # Make sure the user exists
    if not exists(userID):
        log.warning(f"User {userID} doesn't exist.")
        return

    # Get gamemode for db
    mode = scoreUtils.readableGameMode(score_.gameMode)

    # Update total score, playcount and play time
    if score_.playTime is not None:
        realPlayTime = score_.playTime
    else:
        realPlayTime = score_.fullPlayTime

    glob.db.execute(
        "UPDATE users_stats SET total_score_{m}=total_score_{m}+%s, playcount_{m}=playcount_{m}+1, "
        "playtime_{m} = playtime_{m} + %s "
        "WHERE id = %s LIMIT 1".format(m=mode),
        (score_.score, realPlayTime, userID),
    )

    # Calculate new level and update it
    updateLevel(userID, score_.gameMode)

    # Update level, accuracy and ranked score only if we have passed the song
    if score_.passed:
        # Update ranked score
        glob.db.execute(
            "UPDATE users_stats SET ranked_score_{m}=ranked_score_{m}+%s WHERE id = %s LIMIT 1".format(
                m=mode,
            ),
            (score_.rankedScoreIncrease, userID),
        )

        # Update accuracy
        updateAccuracy(userID, score_.gameMode)

        # Update pp
        updatePP(userID, score_.gameMode)


def updateStatsRx(userID, score_):
    """
    Update stats (playcount, total score, ranked score, level bla bla)
    with data relative to a score object

    :param userID:
    :param score_: score object
    :param beatmap_: beatmap object. Optional. If not passed, it'll be determined by score_.
    """

    # Make sure the user exists
    if not exists(userID):
        log.warning(f"User {userID} doesn't exist.")
        return

    # Get gamemode for db
    mode = scoreUtils.readableGameMode(score_.gameMode)

    # Update total score, playcount and play time
    if score_.playTime is not None:
        realPlayTime = score_.playTime
    else:
        realPlayTime = score_.fullPlayTime

    glob.db.execute(
        "UPDATE rx_stats SET total_score_{m}=total_score_{m}+%s, playcount_{m}=playcount_{m}+1, "
        "playtime_{m} = playtime_{m} + %s "
        "WHERE id = %s LIMIT 1".format(m=mode),
        (score_.score, realPlayTime, userID),
    )

    # Calculate new level and update it
    updateLevelRX(userID, score_.gameMode)

    # Update level, accuracy and ranked score only if we have passed the song
    if score_.passed:
        # Update ranked score
        glob.db.execute(
            "UPDATE rx_stats SET ranked_score_{m}=ranked_score_{m}+%s WHERE id = %s LIMIT 1".format(
                m=mode,
            ),
            (score_.rankedScoreIncrease, userID),
        )

        # Update accuracy
        updateAccuracyRX(userID, score_.gameMode)

        # Update pp
        updatePPRelax(userID, score_.gameMode)


def updateStatsAP(userID, score_):
    """
    Update stats (playcount, total score, ranked score, level bla bla)
    with data relative to a score object

    :param userID:
    :param score_: score object
    :param beatmap_: beatmap object. Optional. If not passed, it'll be determined by score_.
    """

    # Make sure the user exists
    if not exists(userID):
        log.warning(f"User {userID} doesn't exist.")
        return

    # Get gamemode for db
    mode = scoreUtils.readableGameMode(score_.gameMode)

    # Update total score, playcount and play time
    if score_.playTime is not None:
        realPlayTime = score_.playTime
    else:
        realPlayTime = score_.fullPlayTime

    glob.db.execute(
        "UPDATE ap_stats SET total_score_{m}=total_score_{m}+%s, playcount_{m}=playcount_{m}+1, "
        "playtime_{m} = playtime_{m} + %s "
        "WHERE id = %s LIMIT 1".format(m=mode),
        (score_.score, realPlayTime, userID),
    )

    # Calculate new level and update it
    updateLevelAP(userID, score_.gameMode)

    # Update level, accuracy and ranked score only if we have passed the song
    if score_.passed:
        # Update ranked score
        glob.db.execute(
            "UPDATE ap_stats SET ranked_score_{m}=ranked_score_{m}+%s WHERE id = %s LIMIT 1".format(
                m=mode,
            ),
            (score_.rankedScoreIncrease, userID),
        )

        # Update accuracy
        updateAccuracyAP(userID, score_.gameMode)

        # Update pp
        updatePPAP(userID, score_.gameMode)


def incrementUserBeatmapPlaycount(userID, gameMode, beatmapID):
    glob.db.execute(
        "INSERT INTO users_beatmap_playcount (user_id, beatmap_id, game_mode, playcount) "
        "VALUES (%s, %s, %s, 1) ON DUPLICATE KEY UPDATE playcount = playcount + 1",
        (userID, beatmapID, gameMode),
    )


def incrementUserBeatmapPlaycountRX(userID, gameMode, beatmapID):
    glob.db.execute(
        "INSERT INTO rx_beatmap_playcount (user_id, beatmap_id, game_mode, playcount) "
        "VALUES (%s, %s, %s, 1) ON DUPLICATE KEY UPDATE playcount = playcount + 1",
        (userID, beatmapID, gameMode),
    )


def incrementUserBeatmapPlaycountAP(userID, gameMode, beatmapID):
    glob.db.execute(
        "INSERT INTO ap_beatmap_playcount (user_id, beatmap_id, game_mode, playcount) "
        "VALUES (%s, %s, %s, 1) ON DUPLICATE KEY UPDATE playcount = playcount + 1",
        (userID, beatmapID, gameMode),
    )


def updateLatestActivity(userID):
    """
    Update userID's latest activity to current UNIX time

    :param userID: user id
    :return:
    """
    glob.db.execute(
        "UPDATE users SET latest_activity = %s WHERE id = %s LIMIT 1",
        [int(time.time()), userID],
    )


def getRankedScore(userID, gameMode):
    """
    Get userID's ranked score relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: ranked score
    """
    mode = scoreUtils.readableGameMode(gameMode)
    result = glob.db.fetch(
        f"SELECT ranked_score_{mode} FROM users_stats WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return result[f"ranked_score_{mode}"]
    else:
        return 0


def getPP(userID, gameMode):
    """
    Get userID's PP relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: pp
    """

    mode = scoreUtils.readableGameMode(gameMode)
    result = glob.db.fetch(
        f"SELECT pp_{mode} FROM users_stats WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return result[f"pp_{mode}"]
    else:
        return 0


def incrementReplaysWatched(userID, gameMode):
    """
    Increment userID's replays watched by others relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return:
    """
    mode = scoreUtils.readableGameMode(gameMode)
    glob.db.execute(
        "UPDATE users_stats SET replays_watched_{mode}=replays_watched_{mode}+1 WHERE id = %s LIMIT 1".format(
            mode=mode,
        ),
        [userID],
    )


def incrementReplaysWatchedRX(userID, gameMode):
    """
    Increment userID's replays watched by others relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return:
    """
    mode = scoreUtils.readableGameMode(gameMode)
    glob.db.execute(
        "UPDATE rx_stats SET replays_watched_{mode}=replays_watched_{mode}+1 WHERE id = %s LIMIT 1".format(
            mode=mode,
        ),
        [userID],
    )


def incrementReplaysWatchedAP(userID, gameMode):
    """
    Increment userID's replays watched by others relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return:
    """
    mode = scoreUtils.readableGameMode(gameMode)
    glob.db.execute(
        "UPDATE ap_stats SET replays_watched_{mode}=replays_watched_{mode}+1 WHERE id = %s LIMIT 1".format(
            mode=mode,
        ),
        [userID],
    )


def getAqn(userID):
    """
    Check if AQN folder was detected for userID

    :param userID: user
    :return: True if hax, False if legit
    """
    result = glob.db.fetch("SELECT aqn FROM users WHERE id = %s LIMIT 1", [userID])
    if result is not None:
        return True if int(result["aqn"]) == 1 else False
    else:
        return False


def setAqn(userID, value=1):
    """
    Set AQN folder status for userID

    :param userID: user
    :param value: new aqn value, default = 1
    :return:
    """
    glob.db.fetch("UPDATE users SET aqn = %s WHERE id = %s LIMIT 1", [value, userID])


def IPLog(userID, ip):
    """
    Log user IP

    :param userID: user id
    :param ip: IP address
    :return:
    """
    glob.db.execute(
        """INSERT INTO ip_user (userid, ip, occurencies) VALUES (%s, %s, '1')
                        ON DUPLICATE KEY UPDATE occurencies = occurencies + 1""",
        [userID, ip],
    )


def checkBanchoSession(userID, ip=""):
    """
    Return True if there is a bancho session for `userID` from `ip`
    If `ip` is an empty string, check if there's a bancho session for that user, from any IP.

    :param userID: user id
    :param ip: ip address. Optional. Default: empty string
    :return: True if there's an active bancho session, else False
    """
    if ip != "":
        return glob.redis.sismember(f"peppy:sessions:{userID}", ip)
    else:
        return glob.redis.exists(f"peppy:sessions:{userID}")


def is2FAEnabled(userID):
    """
    Returns True if 2FA/Google auth 2FA is enable for `userID`

    :userID: user ID
    :return: True if 2fa is enabled, else False
    """
    return (
        glob.db.fetch(
            "SELECT 2fa_totp.userid FROM 2fa_totp WHERE userid = %(userid)s AND enabled = 1 LIMIT 1",
            {"userid": userID},
        )
        is not None
    )


def check2FA(userID, ip):
    """
    Returns True if this IP is untrusted.
    Returns always False if 2fa is not enabled on `userID`

    :param userID: user id
    :param ip: IP address
    :return: True if untrusted, False if trusted or 2fa is disabled.
    """
    if not is2FAEnabled(userID):
        return False

    result = glob.db.fetch(
        "SELECT id FROM ip_user WHERE userid = %s AND ip = %s",
        [userID, ip],
    )
    return True if result is None else False


def isAllowed(userID):
    """
    Check if userID is not banned or restricted

    :param userID: user id
    :return: True if not banned or restricted, otherwise false.
    """
    result = glob.db.fetch(
        "SELECT privileges FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return (result["privileges"] & privileges.USER_NORMAL) and (
            result["privileges"] & privileges.USER_PUBLIC
        )
    else:
        return False


def isRestricted(userID):
    """
    Check if userID is restricted

    :param userID: user id
    :return: True if not restricted, otherwise false.
    """
    result = glob.db.fetch(
        "SELECT privileges FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return (result["privileges"] & privileges.USER_NORMAL) and not (
            result["privileges"] & privileges.USER_PUBLIC
        )
    else:
        return False


def isBanned(userID):
    """
    Check if userID is banned

    :param userID: user id
    :return: True if not banned, otherwise false.
    """
    result = glob.db.fetch(
        "SELECT privileges FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return not (result["privileges"] & 3 > 0)
    else:
        return True


def isLocked(userID):
    """
    Check if userID is locked

    :param userID: user id
    :return: True if not locked, otherwise false.
    """
    result = glob.db.fetch(
        "SELECT privileges FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return (result["privileges"] & privileges.USER_PUBLIC > 0) and (
            result["privileges"] & privileges.USER_NORMAL == 0
        )
    else:
        return True


def ban(userID):
    """
    Ban userID

    :param userID: user id
    :return:
    """
    # Set user as banned in db
    banDateTime = int(time.time())
    glob.db.execute(
        "UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s LIMIT 1",
        [~(privileges.USER_NORMAL | privileges.USER_PUBLIC), banDateTime, userID],
    )

    # Notify bancho about the ban
    glob.redis.publish("peppy:ban", userID)

    # Remove the user from global and country leaderboards
    removeFromLeaderboard(userID)


def unban(userID):
    """
    Unban userID

    :param userID: user id
    :return:
    """
    glob.db.execute(
        "UPDATE users SET privileges = privileges | %s, ban_datetime = 0 WHERE id = %s LIMIT 1",
        [(privileges.USER_NORMAL | privileges.USER_PUBLIC), userID],
    )
    glob.redis.publish("peppy:ban", userID)


def restrict(userID):
    """
    Restrict userID

    :param userID: user id
    :return:
    """
    if not isRestricted(userID):
        # Set user as restricted in db
        banDateTime = int(time.time())
        glob.db.execute(
            "UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s LIMIT 1",
            [~privileges.USER_PUBLIC, banDateTime, userID],
        )

        # Notify bancho about this ban
        glob.redis.publish("peppy:ban", userID)

        # Remove the user from global and country leaderboards
        removeFromLeaderboard(userID)


def unrestrict(userID):
    """
    Unrestrict userID.
    Same as unban().

    :param userID: user id
    :return:
    """
    unban(userID)


def appendNotes(userID, notes, addNl=True, trackDate=True):
    """
    Append `notes` to `userID`'s "notes for CM"

    :param userID: user id
    :param notes: text to append
    :param addNl: if True, prepend \n to notes. Default: True.
    :param trackDate: if True, prepend date and hour to the note. Default: True.
    :return:
    """
    if trackDate:
        notes = f"[{generalUtils.getTimestamp()}] {notes}"
    if addNl:
        notes = f"\n{notes}"
    glob.db.execute(
        "UPDATE users SET notes=CONCAT(COALESCE(notes, ''),%s) WHERE id = %s LIMIT 1",
        [notes, userID],
    )


def getPrivileges(userID):
    """
    Return `userID`'s privileges

    :param userID: user id
    :return: privileges number
    """
    result = glob.db.fetch(
        "SELECT privileges FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is not None:
        return result["privileges"]
    else:
        return 0


def getSilenceEnd(userID):
    """
    Get userID's **ABSOLUTE** silence end UNIX time
    Remember to subtract time.time() if you want to get the actual silence time

    :param userID: user id
    :return: UNIX time
    """
    return glob.db.fetch(
        "SELECT silence_end FROM users WHERE id = %s LIMIT 1",
        [userID],
    )["silence_end"]


def silence(userID, seconds, silenceReason, author=None):
    """
    Silence someone

    :param userID: user id
    :param seconds: silence length in seconds
    :param silenceReason: silence reason shown on website
    :param author: userID of who silenced the user. Default: the server's bot.
    :return:
    """

    if author is None:
        author = settings.PS_BOT_USER_ID
    # db qurey
    silenceEndTime = int(time.time()) + seconds
    glob.db.execute(
        "UPDATE users SET silence_end = %s, silence_reason = %s WHERE id = %s LIMIT 1",
        [silenceEndTime, silenceReason, userID],
    )

    # Log
    targetUsername = getUsername(userID)
    # TODO: exists check im drunk rn i need to sleep (stampa piede ubriaco confirmed)
    if seconds > 0:
        log.info(
            'has silenced {} for {} seconds for the following reason: "{}"'.format(
                targetUsername,
                seconds,
                silenceReason,
            ),
        )
    else:
        log.rap(author, f"has removed {targetUsername}'s silence", True)


def getTotalScore(userID, gameMode):
    """
    Get `userID`'s total score relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: total score
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch(
        "SELECT total_score_" + modeForDB + " FROM users_stats WHERE id = %s LIMIT 1",
        [userID],
    )["total_score_" + modeForDB]


def getAccuracy(userID, gameMode):
    """
    Get `userID`'s average accuracy relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: accuracy
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch(
        "SELECT avg_accuracy_" + modeForDB + " FROM users_stats WHERE id = %s LIMIT 1",
        [userID],
    )["avg_accuracy_" + modeForDB]


def getGameRank(userID, gameMode):
    """
    Get `userID`'s **in-game rank** (eg: #1337) relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: game rank
    """
    position = glob.redis.zrevrank(
        f"ripple:leaderboard:{gameModes.getGameModeForDB(gameMode)}",
        userID,
    )
    if position is None:
        return 0
    else:
        return int(position) + 1


def getGameRankRx(userID, gameMode):
    """
    Get `userID`'s **in-game rank** (eg: #1337) relative to gameMode
    :param userID: user id
    :param gameMode: game mode number
    :return: game rank
    """
    position = glob.redis.zrevrank(
        f"ripple:leaderboard_relax:{gameModes.getGameModeForDB(gameMode)}",
        userID,
    )
    if position is None:
        return 0
    else:
        return int(position) + 1


def getGameRankAP(userID, gameMode):
    """
    Get `userID`'s **in-game rank** (eg: #1337) relative to gameMode
    :param userID: user id
    :param gameMode: game mode number
    :return: game rank
    """
    position = glob.redis.zrevrank(
        f"ripple:leaderboard_ap:{gameModes.getGameModeForDB(gameMode)}",
        userID,
    )  # REMEMBER TO ADD REDIS FOR THIS
    if position is None:
        return 0
    else:
        return int(position) + 1


def getPlaycount(userID, gameMode):
    """
    Get `userID`'s playcount relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: playcount
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch(
        "SELECT playcount_" + modeForDB + " FROM users_stats WHERE id = %s LIMIT 1",
        [userID],
    )["playcount_" + modeForDB]


def getPlaycountRX(userID, gameMode):
    """
    Get `userID`'s playcount relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: playcount
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch(
        "SELECT playcount_" + modeForDB + " FROM rx_stats WHERE id = %s LIMIT 1",
        [userID],
    )["playcount_" + modeForDB]


def getPlaycountAP(userID, gameMode):
    """
    Get `userID`'s playcount relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: playcount
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch(
        "SELECT playcount_" + modeForDB + " FROM ap_stats WHERE id = %s LIMIT 1",
        [userID],
    )["playcount_" + modeForDB]


def getFriendList(userID):
    """
    Get `userID`'s friendlist

    :param userID: user id
    :return: list with friends userIDs. [0] if no friends.
    """
    # Get friends from db
    friends = glob.db.fetchAll(
        "SELECT user2 FROM users_relationships WHERE user1 = %s",
        [userID],
    )

    if friends is None or len(friends) == 0:
        # We have no friends, return 0 list
        return [0]
    else:
        # Get only friends
        friends = [i["user2"] for i in friends]

        # Return friend IDs
        return friends


def addFriend(userID, friendID):
    """
    Add `friendID` to `userID`'s friend list

    :param userID: user id
    :param friendID: new friend
    :return:
    """
    # Make sure we aren't adding us to our friends
    if userID == friendID:
        return

    # check user isn't already a friend of ours
    if (
        glob.db.fetch(
            "SELECT id FROM users_relationships WHERE user1 = %s AND user2 = %s LIMIT 1",
            [userID, friendID],
        )
        is not None
    ):
        return

    # Set new value
    glob.db.execute(
        "INSERT INTO users_relationships (user1, user2) VALUES (%s, %s)",
        [userID, friendID],
    )


def removeFriend(userID, friendID):
    """
    Remove `friendID` from `userID`'s friend list

    :param userID: user id
    :param friendID: old friend
    :return:
    """
    # Delete user relationship. We don't need to check if the relationship was there, because who gives a shit,
    # if they were not friends and they don't want to be anymore, be it. ¯\_(ツ)_/¯
    # TODO: LIMIT 1
    glob.db.execute(
        "DELETE FROM users_relationships WHERE user1 = %s AND user2 = %s",
        [userID, friendID],
    )


def getCountry(userID):
    """
    Get `userID`'s country **(two letters)**.

    :param userID: user id
    :return: country code (two letters)
    """
    return glob.db.fetch(
        "SELECT country FROM users_stats WHERE id = %s LIMIT 1",
        [userID],
    )["country"]


def setCountry(userID, country):
    """
    Set userID's country

    :param userID: user id
    :param country: country letters
    :return:
    """
    glob.db.execute(
        "UPDATE users_stats SET country = %s WHERE id = %s LIMIT 1",
        [country, userID],
    )


def logIP(userID, ip):
    """
    User IP log
    USED FOR MULTIACCOUNT DETECTION

    :param userID: user id
    :param ip: IP address
    :return:
    """
    glob.db.execute(
        """INSERT INTO ip_user (userid, ip, occurencies) VALUES (%s, %s, 1)
                        ON DUPLICATE KEY UPDATE occurencies = occurencies + 1""",
        [userID, ip],
    )


def saveBanchoSession(userID, ip):
    """
    Save userid and ip of this token in redis
    Used to cache logins on LETS requests

    :param userID: user ID
    :param ip: IP address
    :return:
    """
    glob.redis.sadd(f"peppy:sessions:{userID}", ip)


def deleteBanchoSessions(userID, ip):
    """
    Delete this bancho session from redis

    :param userID: user id
    :param ip: IP address
    :return:
    """
    glob.redis.srem(f"peppy:sessions:{userID}", ip)


def setPrivileges(userID, priv):
    """
    Set userID's privileges in db

    :param userID: user id
    :param priv: privileges number
    :return:
    """
    glob.db.execute(
        "UPDATE users SET privileges = %s WHERE id = %s LIMIT 1",
        [priv, userID],
    )


def getGroupPrivileges(groupName):
    """
    Returns the privileges number of a group, by its name

    :param groupName: name of the group
    :return: privilege integer or `None` if the group doesn't exist
    """
    groupPrivileges = glob.db.fetch(
        "SELECT privileges FROM privileges_groups WHERE name = %s LIMIT 1",
        [groupName],
    )
    if groupPrivileges is None:
        return None
    return groupPrivileges["privileges"]


def isInPrivilegeGroup(userID, groupName):
    """
    Check if `userID` is in a privilege group.
    Donor privilege is ignored while checking for groups.

    :param userID: user id
    :param groupName: privilege group name
    :return: True if `userID` is in `groupName`, else False
    """
    groupPrivileges = getGroupPrivileges(groupName)
    if groupPrivileges is None:
        return False
    try:
        userToken = glob.tokens.getTokenFromUserID(userID)
    except AttributeError:
        # LETS compatibility
        userToken = None

    if userToken is not None:
        userPrivileges = userToken.privileges
    else:
        userPrivileges = getPrivileges(userID)
    return userPrivileges & groupPrivileges == groupPrivileges


def isInAnyPrivilegeGroup(userID, groups):
    """
    Checks if a user is in at least one of the specified groups

    :param userID: id of the user
    :param groups: groups list or tuple
    :return: `True` if `userID` is in at least one of the specified groups, otherwise `False`
    """
    userPrivileges = getPrivileges(userID)
    return any(
        userPrivileges & x == x
        for x in (getGroupPrivileges(y) for y in groups)
        if x is not None
    )


def logHardware(
    user_id: int,
    hashes: list[str],
    is_restricted: bool,
    activation: bool = False,
    bypass_restrict: bool = False,
) -> bool:
    """
    Hardware log
    USED FOR MULTIACCOUNT DETECTION


    :param userID: user id
    :param hashes:    Peppy's botnet (client data) structure (new line = "|", already split)
                                    [0] osu! version
                                    [1] plain mac addressed, separated by "."
                                    [2] mac addresses hash set
                                    [3] unique ID
                                    [4] disk ID
    :param activation: if True, set this hash as used for activation. Default: False.
    :return: True if hw is not banned, otherwise false
    """
    # Make sure the strings are not empty
    if len(hashes) != 5 or not all(hashes[2:5]):
        log.warning(f"User {user_id} has sent an empty hwid hash set {hashes}.")
        return False

    if not is_restricted:
        # Wine users. Only the unique_id is somewhat reliable.
        if hashes[2] == "b4ec3c4334a0249dae95c284ec5983df":
            matching_users = glob.db.fetchAll(
                "SELECT DISTINCT u.id AS userid, u.username AS username FROM hw_user h INNER JOIN users u ON h.userid = u.id "
                "WHERE h.userid != %s AND h.unique_id = %s",
                (user_id, hashes[3]),
            )

        else:
            matching_users = glob.db.fetchAll(
                "SELECT DISTINCT u.id AS userid, u.username AS username FROM hw_user h INNER JOIN users u ON h.userid = u.id "
                "WHERE h.userid != %s AND (h.mac = %s AND h.unique_id = %s AND h.disk_id = %s) ",
                (user_id, hashes[2], hashes[3], hashes[4]),
            )

        matching_users = list(matching_users)

        if matching_users:
            # User has a matching hwid, ban him
            log.warning(
                f"User {user_id} has a matching hwid with user IDs: {matching_users!r}.",
            )

            if not bypass_restrict:
                # Detect the earliest account ID to restrict, ban rest
                earliest_user = min(matching_users, key=lambda x: x["userid"])
                matching_users.remove(earliest_user)
                matching_str = ", ".join(
                    f"{i['username']} ({i['userid']})" for i in matching_users
                )

                restrict_with_log(
                    earliest_user["userid"],
                    "HWID Match with another user.",
                    f"The sent hwids ({hashes!r}) have matched with the following users: {matching_str}. "
                    "This implies that they are likely to be using a multiaccount.",
                )

                # Ban the multiaccounts.
                for user in matching_users:
                    ban_with_log(
                        user["userid"],
                        "Multiaccount detected by HWID match.",
                        f"The sent hwids ({hashes!r}) which exactly matched with an earlier account: "
                        f"{earliest_user['username']} ({earliest_user['userid']}). "
                        "This implies that they are likely to be using a multiaccount. As a result, this "
                        "account has been banned, while the earlier account has been restricted.",
                    )

    # Update hash set occurencies
    # Our database doesnt have any fancy keys.
    exists = glob.db.fetch(
        "SELECT id FROM hw_user WHERE userid = %s AND mac = %s AND unique_id = %s AND disk_id = %s",
        (
            user_id,
            hashes[2],
            hashes[3],
            hashes[4],
        ),
    )
    if exists:
        glob.db.execute(
            "UPDATE hw_user SET occurencies = occurencies + 1 WHERE id = %s LIMIT 1",
            (exists["id"],),
        )
    else:
        glob.db.execute(
            """
                INSERT INTO hw_user (id, userid, mac, unique_id, disk_id, occurencies) VALUES (NULL, %s, %s, %s, %s, 1)
            """,
            [user_id, hashes[2], hashes[3], hashes[4]],
        )

    # Optionally, set this hash as 'used for activation'
    if activation:
        glob.db.execute(
            "UPDATE hw_user SET activated = 1 WHERE userid = %s AND mac = %s AND unique_id = %s AND disk_id = %s"
            "LIMIT 1",
            [user_id, hashes[2], hashes[3], hashes[4]],
        )

    # Access granted, abbiamo impiegato 3 giorni
    # We grant access even in case of login from banned HWID
    # because we call restrict() above so there's no need to deny the access.
    return True


def resetPendingFlag(userID, success=True):
    """
    Remove pending flag from an user.

    :param userID: user id
    :param success: if True, set USER_PUBLIC and USER_NORMAL flags too
    """
    glob.db.execute(
        "UPDATE users SET privileges = privileges & %s WHERE id = %s LIMIT 1",
        [~privileges.USER_PENDING_VERIFICATION, userID],
    )
    if success:
        glob.db.execute(
            "UPDATE users SET privileges = privileges | %s WHERE id = %s LIMIT 1",
            [(privileges.USER_PUBLIC | privileges.USER_NORMAL), userID],
        )


def verifyUser(userID, hashes):
    """
    Activate `userID`'s account.

    :param userID: user id
    :param hashes:     Peppy's botnet (client data) structure (new line = "|", already split)
                                    [0] osu! version
                                    [1] plain mac addressed, separated by "."
                                    [2] mac addresses hash set
                                    [3] unique ID
                                    [4] disk ID
    :return: True if verified successfully, else False (multiaccount)
    """
    # Check for valid hash set
    for i in hashes[2:5]:
        if i == "":
            log.warning(
                "Invalid hash set ({}) for user {} while verifying the account".format(
                    str(hashes),
                    userID,
                ),
                "bunk",
            )
            return False

    # Get username
    username = getUsername(userID)

    # Make sure there are no other accounts activated with this exact mac/unique id/hwid
    if (
        hashes[2] == "b4ec3c4334a0249dae95c284ec5983df"
        or hashes[4] == "ffae06fb022871fe9beb58b005c5e21d"
    ):
        # Running under wine, check only by uniqueid
        log.info(
            f"{username} ({userID}) ha triggerato Sannino\nUsual wine mac address hash: b4ec3c4334a0249dae95c284ec5983df\nUsual wine disk id: ffae06fb022871fe9beb58b005c5e21d",
        )
        log.debug("Veryfing with Linux/Mac hardware")
        match = glob.db.fetchAll(
            "SELECT userid FROM hw_user WHERE unique_id = %(uid)s AND userid != %(userid)s AND activated = 1 LIMIT 1",
            {"uid": hashes[3], "userid": userID},
        )
    else:
        # Running under windows, full check
        log.debug("Veryfing with Windows hardware")
        match = glob.db.fetchAll(
            "SELECT userid FROM hw_user WHERE mac = %(mac)s AND unique_id = %(uid)s AND disk_id = %(diskid)s AND userid != %(userid)s AND activated = 1 LIMIT 1",
            {"mac": hashes[2], "uid": hashes[3], "diskid": hashes[4], "userid": userID},
        )

    if match:
        # This is a multiaccount, restrict other account and ban this account

        # Get original userID and username (lowest ID)
        originalUserID = match[0]["userid"]
        originalUsername = getUsername(originalUserID)

        # Now we check if have a bypass on.
        user_data = glob.db.fetch(
            f"SELECT bypass_hwid FROM users WHERE id = {userID} LIMIT 1",
        )

        # If they are explicitly allowed to multiacc
        if user_data["bypass_hwid"]:
            log.warning(f"Allowed user {username} to bypass hwid check.")
            return True

        # Ban this user and append notes
        ban(userID)  # this removes the USER_PENDING_VERIFICATION flag too
        appendNotes(
            userID,
            "{}'s multiaccount ({}), found HWID match while verifying account ({})".format(
                originalUsername,
                originalUserID,
                hashes[2:5],
            ),
        )
        appendNotes(
            originalUserID,
            f"Has created multiaccount {username} ({userID})",
        )

        # Restrict the original
        restrict(originalUserID)

        # Discord message
        log.warning(
            "User **{originalUsername}** ({originalUserID}) has been restricted because he has created multiaccount **{username}** ({userID}). The multiaccount has been banned.".format(
                originalUsername=originalUsername,
                originalUserID=originalUserID,
                username=username,
                userID=userID,
            ),
        )

        # Disallow login
        return False
    else:
        # No matches found, set USER_PUBLIC and USER_NORMAL flags and reset USER_PENDING_VERIFICATION flag
        resetPendingFlag(userID)

        # Allow login
        return True


def hasVerifiedHardware(userID):
    """
    Checks if `userID` has activated his account through HWID

    :param userID: user id
    :return: True if hwid activation data is in db, otherwise False
    """
    data = glob.db.fetch(
        "SELECT id FROM hw_user WHERE userid = %s AND activated = 1 LIMIT 1",
        [userID],
    )
    if data is not None:
        return True
    return False


def getDonorExpire(userID):
    """
    Return `userID`'s donor expiration UNIX timestamp

    :param userID: user id
    :return: donor expiration UNIX timestamp
    """
    data = glob.db.fetch(
        "SELECT donor_expire FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if data is not None:
        return data["donor_expire"]
    return 0


class invalidUsernameError(Exception):
    pass


class usernameAlreadyInUseError(Exception):
    pass


def safeUsername(username):
    """
    Return `username`'s safe username
    (all lowercase and underscores instead of spaces)

    :param username: unsafe username
    :return: safe username
    """
    return username.lower().strip().replace(" ", "_")


def removeFromLeaderboard(userID):
    """
    Removes userID from global and country leaderboards.

    :param userID:
    :return:
    """
    # Remove the user from global and country leaderboards, for every mode
    country = getCountry(userID).lower()
    for mode in ["std", "taiko", "ctb", "mania"]:
        glob.redis.zrem(f"ripple:leaderboard:{mode}", str(userID))
        glob.redis.zrem(f"ripple:leaderboard_relax:{mode}", str(userID))
        glob.redis.zrem(f"ripple:leaderboard_ap:{mode}", str(userID))
        if country is not None and len(country) > 0 and country != "xx":
            glob.redis.zrem(
                f"ripple:leaderboard:{mode}:{country}",
                str(userID),
            )
            glob.redis.zrem(
                f"ripple:leaderboard_relax:{mode}:{country}",
                str(userID),
            )
            glob.redis.zrem(
                f"ripple:leaderboard_ap:{mode}:{country}",
                str(userID),
            )


def deprecateTelegram2Fa(userID):
    """
    Checks whether the user has enabled telegram 2fa on his account.
    If so, disables 2fa and returns True.
    If not, return False.

    :param userID: id of the user
    :return: True if 2fa has been disabled from the account otherwise False
    """
    try:
        telegram2Fa = glob.db.fetch(
            "SELECT id FROM 2fa_telegram WHERE userid = %s LIMIT 1",
            (userID,),
        )
    except ProgrammingError:
        # The table doesnt exist
        return False

    if telegram2Fa is not None:
        glob.db.execute("DELETE FROM 2fa_telegram WHERE userid = %s LIMIT 1", (userID,))
        return True
    return False


def unlockAchievement(userID, achievementID):
    glob.db.execute(
        "INSERT INTO users_achievements (user_id, achievement_id, `time`) VALUES"
        "(%s, %s, %s)",
        [userID, achievementID, int(time.time())],
    )


def getAchievementsVersion(userID):
    result = glob.db.fetch(
        "SELECT achievements_version FROM users WHERE id = %s LIMIT 1",
        [userID],
    )
    if result is None:
        return None
    return result["achievements_version"]


def updateAchievementsVersion(userID):
    glob.db.execute(
        "UPDATE users SET achievements_version = %s WHERE id = %s LIMIT 1",
        [glob.ACHIEVEMENTS_VERSION, userID],
    )


def getClan(userID):
    """
    Get userID's clan

    :param userID: user id
    :return: username or None
    """
    clanInfo = glob.db.fetch(
        "SELECT clans.tag, clans.id, user_clans.clan, user_clans.user FROM user_clans LEFT JOIN clans ON clans.id = user_clans.clan WHERE user_clans.user = %s LIMIT 1",
        [userID],
    )
    username = getUsername(userID)

    if clanInfo is None:
        return username
    return "[" + clanInfo["tag"] + "] " + username


def updateTotalHits(userID=0, gameMode=gameModes.STD, newHits=0, score=None):
    if score is None and userID == 0:
        raise ValueError("Either score or userID must be provided")
    if score is not None:
        newHits = score.c50 + score.c100 + score.c300
        gameMode = score.gameMode
        userID = score.playerUserID
    glob.db.execute(
        "UPDATE users_stats SET total_hits_{gm} = total_hits_{gm} + %s WHERE id = %s LIMIT 1".format(
            gm=gameModes.getGameModeForDB(gameMode),
        ),
        (newHits, userID),
    )


def updateTotalHitsRX(userID=0, gameMode=gameModes.STD, newHits=0, score=None):
    if score is None and userID == 0:
        raise ValueError("Either score or userID must be provided")
    if score is not None:
        newHits = score.c50 + score.c100 + score.c300
        gameMode = score.gameMode
        userID = score.playerUserID
    glob.db.execute(
        "UPDATE rx_stats SET total_hits_{gm} = total_hits_{gm} + %s WHERE id = %s LIMIT 1".format(
            gm=gameModes.getGameModeForDB(gameMode),
        ),
        (newHits, userID),
    )


def updateTotalHitsAP(userID=0, gameMode=gameModes.STD, newHits=0, score=None):
    if score is None and userID == 0:
        raise ValueError("Either score or userID must be provided")
    if score is not None:
        newHits = score.c50 + score.c100 + score.c300
        gameMode = score.gameMode
        userID = score.playerUserID
    glob.db.execute(
        "UPDATE ap_stats SET total_hits_{gm} = total_hits_{gm} + %s WHERE id = %s LIMIT 1".format(
            gm=gameModes.getGameModeForDB(gameMode),
        ),
        (newHits, userID),
    )


def insert_ban_log(
    user_id: int,
    summary: str,
    detail: str,
    prefix: bool = True,
    from_id: Optional[int] = None,
) -> None:
    """Inserts a ban log for a user into the database.

    Args:
        user_id (int): The ID of the user to assign the log to.
        summary (str): A short description of the reason.
        detail (str): A more detailed, in-depth description of the reason.
        prefix (bool, optional): Whether the detail should be prefixed by
            the peppy signature. Defaults to True.
        from_id (int, optional): The ID of the user who banned the user.
            Defaults to the configured bot.
    """

    if from_id is None:
        from_id = settings.PS_BOT_USER_ID

    if prefix:
        detail = "pep.py Autoban: " + detail

    glob.db.execute(
        "INSERT INTO ban_logs (from_id, to_id, summary, detail) VALUES (%s, %s, %s, %s)",
        (
            from_id,
            user_id,
            summary,
            detail,
        ),
    )


def restrict_with_log(
    user_id: int,
    summary: str,
    detail: str,
    prefix: bool = True,
    from_id: Optional[int] = None,
) -> None:
    """Restricts the user alongside inserting a log into the database.

    Args:
        user_id (int): The ID of the user to assign the log to.
        summary (str): A short description of the reason.
        detail (str): A more detailed, in-depth description of the reason.
        prefix (bool, optional): Whether the detail should be prefixed by
            the peppy signature. Defaults to True.
        from_id (int, optional): The ID of the user who banned the user.
            Defaults to the configured bot.
    """

    if from_id is None:
        from_id = settings.PS_BOT_USER_ID

    glob.db.execute(
        f"UPDATE users SET privileges = privileges & ~{privileges.USER_PUBLIC}, "
        "ban_datetime = UNIX_TIMESTAMP() WHERE id = %s LIMIT 1",
        (user_id,),
    )
    glob.redis.publish("peppy:ban", user_id)
    removeFromLeaderboard(user_id)

    insert_ban_log(user_id, summary, detail, prefix, from_id)


def ban_with_log(
    user_id: int,
    summary: str,
    detail: str,
    prefix: bool = True,
    from_id: Optional[int] = None,
) -> None:
    """Bans the user alongside inserting a log into the database.

    Args:
        user_id (int): The ID of the user to assign the log to.
        summary (str): A short description of the reason.
        detail (str): A more detailed, in-depth description of the reason.
        prefix (bool, optional): Whether the detail should be prefixed by
            the peppy signature. Defaults to True.
        from_id (int, optional): The ID of the user who banned the user.
            Defaults to the configured bot.
    """

    if from_id is None:
        from_id = settings.PS_BOT_USER_ID

    glob.db.execute(
        f"UPDATE users SET privileges = 0, "
        "ban_datetime = UNIX_TIMESTAMP() WHERE id = %s LIMIT 1",
        (user_id,),
    )
    glob.redis.publish("peppy:ban", user_id)
    removeFromLeaderboard(user_id)

    insert_ban_log(user_id, summary, detail, prefix, from_id)
