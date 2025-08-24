from __future__ import annotations

import logging
import time
from typing import Optional

import settings
from common import generalUtils
from common.constants import gameModes, mods, privileges
from common.ripple import scoreUtils
from objects import glob

logger = logging.getLogger(__name__)


def get_id_safe(safe_username: str) -> Optional[int]:
    """Get user ID from a safe username.

    Args:
        safe_username: Safe username (lowercase, underscores instead of spaces).

    Returns:
        User ID if the user exists, None otherwise.
    """
    result = glob.db.fetch(
        "SELECT id FROM users WHERE username_safe = %s LIMIT 1",
        [safe_username],
    )
    if result is not None:
        return result["id"]
    return None


def get_id(username: str) -> int:
    """Get username's user ID from userID redis cache or database.

    Gets userID from redis cache (if cache hit) or from database (and cache it
    for other requests) if cache miss.

    Args:
        username: Username to get ID for.

    Returns:
        User ID or 0 if user doesn't exist.
    """
    # Get userID from redis
    username_safe = safe_username(username)
    user_id = glob.redis.get(f"ripple:userid_cache:{username_safe}")

    if user_id is None:
        # If it's not in redis, get it from mysql
        user_id = get_id_safe(username_safe)

        # If it's invalid, return 0
        if user_id is None:
            return 0

        # Otherwise, save it in redis and return it
        glob.redis.set(
            f"ripple:userid_cache:{username_safe}",
            user_id,
            3600,
        )  # expires in 1 hour
        return user_id

    # Return userid from redis
    return int(user_id)


def get_username(user_id: int) -> Optional[str]:
    """Get userID's username.

    Args:
        user_id: User ID.

    Returns:
        Username or None if user doesn't exist.
    """
    result = glob.db.fetch(
        "SELECT username FROM users WHERE id = %s LIMIT 1", [user_id]
    )
    if result is None:
        return None
    return result["username"]


def get_friend_list(user_id: int) -> list[int]:
    """Get user's friend list.

    Args:
        user_id: User ID.

    Returns:
        List with friends user IDs. [0] if no friends.
    """
    # Get friends from db
    friends = glob.db.fetchAll(
        "SELECT user2 FROM users_relationships WHERE user1 = %s",
        [user_id],
    )

    if friends is None or len(friends) == 0:
        # We have no friends, return 0 list
        return [0]
    else:
        # Get only friends
        friends = [i["user2"] for i in friends]

        # Return friend IDs
        return friends


def add_friend(user_id: int, friend_id: int) -> None:
    """Add friend to user's friend list.

    Args:
        user_id: User ID.
        friend_id: New friend's user ID.
    """
    # Make sure we aren't adding us to our friends
    if user_id == friend_id:
        return

    # check user isn't already a friend of ours
    if (
        glob.db.fetch(
            "SELECT id FROM users_relationships WHERE user1 = %s AND user2 = %s LIMIT 1",
            [user_id, friend_id],
        )
        is not None
    ):
        return

    # Set new value
    glob.db.execute(
        "INSERT INTO users_relationships (user1, user2) VALUES (%s, %s)",
        [user_id, friend_id],
    )


def remove_friend(user_id: int, friend_id: int) -> None:
    """Remove friend from user's friend list.

    Args:
        user_id: User ID.
        friend_id: Friend's user ID to remove.
    """
    # Delete user relationship. We don't need to check if the relationship was there
    # TODO: LIMIT 1
    glob.db.execute(
        "DELETE FROM users_relationships WHERE user1 = %s AND user2 = %s",
        [user_id, friend_id],
    )


def get_silence_end(user_id: int) -> int:
    """Get user's absolute silence end UNIX time.

    Remember to subtract time.time() if you want to get the actual silence time.

    Args:
        user_id: User ID.

    Returns:
        UNIX timestamp of silence end.
    """
    return glob.db.fetch(
        "SELECT silence_end FROM users WHERE id = %s LIMIT 1",
        [user_id],
    )["silence_end"]


def silence(
    user_id: int, seconds: int, silence_reason: str, author: Optional[int] = None
) -> None:
    """Silence a user.

    Args:
        user_id: User ID to silence.
        seconds: Silence length in seconds.
        silence_reason: Silence reason shown on website.
        author: User ID of who silenced the user. Defaults to the server's bot.
    """
    if author is None:
        author = settings.PS_BOT_USER_ID

    silence_end_time = int(time.time()) + seconds
    glob.db.execute(
        "UPDATE users SET silence_end = %s, silence_reason = %s WHERE id = %s LIMIT 1",
        [silence_end_time, silence_reason, user_id],
    )

    # Log
    target_username = get_username(user_id)
    if seconds > 0:
        logger.info(
            "A user has been silenced.",
            extra={
                "target_username": target_username,
                "author": author,
                "seconds": seconds,
                "silence_reason": silence_reason,
            },
        )
    else:
        logger.info(
            "A silence has been removed.",
            extra={
                "target_username": target_username,
                "author": author,
            },
        )


def is_banned(user_id: int) -> bool:
    """Check if user is banned.

    Args:
        user_id: User ID.

    Returns:
        True if user is banned, False otherwise.
    """
    result = glob.db.fetch(
        "SELECT privileges FROM users WHERE id = %s LIMIT 1",
        [user_id],
    )
    if result is not None:
        return not (result["privileges"] & 3 > 0)
    else:
        return True


def ban(user_id: int) -> None:
    """Ban a user.

    Args:
        user_id: User ID to ban.
    """
    # Set user as banned in db
    ban_datetime = int(time.time())
    glob.db.execute(
        "UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s LIMIT 1",
        [~(privileges.USER_NORMAL | privileges.USER_PUBLIC), ban_datetime, user_id],
    )

    # Notify bancho about the ban
    glob.redis.publish("peppy:ban", user_id)

    # Remove the user from global and country leaderboards
    remove_from_leaderboard(user_id)


def unban(user_id: int) -> None:
    """Unban a user.

    Args:
        user_id: User ID to unban.
    """
    glob.db.execute(
        "UPDATE users SET privileges = privileges | %s, ban_datetime = 0 WHERE id = %s LIMIT 1",
        [(privileges.USER_NORMAL | privileges.USER_PUBLIC), user_id],
    )
    glob.redis.publish("peppy:ban", user_id)


def unrestrict(user_id: int) -> None:
    """Unrestrict a user. Same as unban().

    Args:
        user_id: User ID to unrestrict.
    """
    unban(user_id)


def save_bancho_session(user_id: int, ip: str) -> None:
    """Save user ID and IP of this token in redis.

    Used to cache logins on LETS requests.

    Args:
        user_id: User ID.
        ip: IP address.
    """
    glob.redis.sadd(f"peppy:sessions:{user_id}", ip)


def delete_bancho_sessions(user_id: int, ip: str) -> None:
    """Delete bancho session from redis.

    Args:
        user_id: User ID.
        ip: IP address.
    """
    glob.redis.srem(f"peppy:sessions:{user_id}", ip)


def get_pp(user_id: int, game_mode: int) -> int:
    """Get user's PP relative to game mode.

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        User's PP for the specified game mode.
    """
    mode = scoreUtils.readableGameMode(game_mode)
    result = glob.db.fetch(
        f"SELECT pp_{mode} FROM users_stats WHERE id = %s LIMIT 1",
        [user_id],
    )
    if result is not None:
        return result[f"pp_{mode}"]
    else:
        return 0


def get_user_stats(user_id: int, game_mode: int) -> dict:
    """Get all user stats relative to game mode.

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        Dictionary with user stats including game rank.
    """
    mode_for_db = gameModes.getGameModeForDB(game_mode)

    # Get stats
    stats = glob.db.fetch(
        """SELECT
                        ranked_score_{gm} AS rankedScore,
                        avg_accuracy_{gm} AS accuracy,
                        playcount_{gm} AS playcount,
                        total_score_{gm} AS totalScore,
                        pp_{gm} AS pp
                        FROM users_stats WHERE id = %s LIMIT 1""".format(
            gm=mode_for_db,
        ),
        [user_id],
    )

    # Get game rank
    stats["gameRank"] = get_game_rank(user_id, game_mode)

    # Return stats + game rank
    return stats


def get_user_stats_rx(user_id: int, game_mode: int) -> dict:
    """Get all user stats relative to game mode (Relax mode).

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        Dictionary with user stats including game rank.
    """
    mode_for_db = gameModes.getGameModeForDB(game_mode)

    # Get stats
    if game_mode == 3:
        stats = glob.db.fetch(
            """SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM users_stats WHERE id = %s LIMIT 1""".format(
                gm=mode_for_db,
            ),
            [user_id],
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
                gm=mode_for_db,
            ),
            [user_id],
        )

    # Get game rank
    stats["gameRank"] = get_game_rank_rx(user_id, game_mode)

    # Return stats + game rank
    return stats


def get_user_stats_ap(user_id: int, game_mode: int) -> dict:
    """Get all user stats relative to game mode (Auto Pilot mode).

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        Dictionary with user stats including game rank.
    """
    mode_for_db = gameModes.getGameModeForDB(game_mode)

    # Get stats
    if game_mode == 3:  # mania
        stats = glob.db.fetch(
            """SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM users_stats WHERE id = %s LIMIT 1""".format(
                gm=mode_for_db,
            ),
            [user_id],
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
                gm=mode_for_db,
            ),
            [user_id],
        )

    # Get game rank
    stats["gameRank"] = get_game_rank_ap(user_id, game_mode)

    # Return stats + game rank
    return stats


def get_game_rank(user_id: int, game_mode: int) -> int:
    """Get user's in-game rank relative to game mode.

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        User's in-game rank (e.g., #1337). Returns 0 if not ranked.
    """
    position = glob.redis.zrevrank(
        f"ripple:leaderboard:{gameModes.getGameModeForDB(game_mode)}",
        user_id,
    )
    if position is None:
        return 0
    else:
        return int(position) + 1


def get_game_rank_rx(user_id: int, game_mode: int) -> int:
    """Get user's in-game rank relative to game mode (Relax mode).

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        User's in-game rank (e.g., #1337). Returns 0 if not ranked.
    """
    position = glob.redis.zrevrank(
        f"ripple:leaderboard_relax:{gameModes.getGameModeForDB(game_mode)}",
        user_id,
    )
    if position is None:
        return 0
    else:
        return int(position) + 1


def get_game_rank_ap(user_id: int, game_mode: int) -> int:
    """Get user's in-game rank relative to game mode (Auto Pilot mode).

    Args:
        user_id: User ID.
        game_mode: Game mode number.

    Returns:
        User's in-game rank (e.g., #1337). Returns 0 if not ranked.
    """
    position = glob.redis.zrevrank(
        f"ripple:leaderboard_ap:{gameModes.getGameModeForDB(game_mode)}",
        user_id,
    )
    if position is None:
        return 0
    else:
        return int(position) + 1


def safe_username(username: str) -> str:
    """Convert username to safe username format.

    Converts to lowercase and replaces spaces with underscores.

    Args:
        username: Unsafe username.

    Returns:
        Safe username (lowercase, underscores instead of spaces).
    """
    return username.lower().strip().replace(" ", "_")


def remove_from_leaderboard(user_id: int) -> None:
    """Remove user from global and country leaderboards.

    Args:
        user_id: User ID to remove from leaderboards.
    """
    # Remove the user from global and country leaderboards, for every mode
    country = get_country(user_id).lower()
    for mode in ["std", "taiko", "ctb", "mania"]:
        glob.redis.zrem(f"ripple:leaderboard:{mode}", str(user_id))
        glob.redis.zrem(f"ripple:leaderboard_relax:{mode}", str(user_id))
        glob.redis.zrem(f"ripple:leaderboard_ap:{mode}", str(user_id))
        if country is not None and len(country) > 0 and country != "xx":
            glob.redis.zrem(
                f"ripple:leaderboard:{mode}:{country}",
                str(user_id),
            )
            glob.redis.zrem(
                f"ripple:leaderboard_relax:{mode}:{country}",
                str(user_id),
            )
            glob.redis.zrem(
                f"ripple:leaderboard_ap:{mode}:{country}",
                str(user_id),
            )


def get_country(user_id: int) -> str:
    """Get user's country code.

    Args:
        user_id: User ID.

    Returns:
        Two-letter country code.
    """
    return glob.db.fetch(
        "SELECT country FROM users_stats WHERE id = %s LIMIT 1",
        [user_id],
    )["country"]


def insert_ban_log(
    user_id: int,
    summary: str,
    detail: str,
    prefix: bool = True,
    from_id: Optional[int] = None,
) -> None:
    """Insert a ban log for a user into the database.

    Args:
        user_id: The ID of the user to assign the log to.
        summary: A short description of the reason.
        detail: A more detailed, in-depth description of the reason.
        prefix: Whether the detail should be prefixed by the peppy signature.
            Defaults to True.
        from_id: The ID of the user who banned the user.
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
    """Restrict the user alongside inserting a log into the database.

    Args:
        user_id: The ID of the user to assign the log to.
        summary: A short description of the reason.
        detail: A more detailed, in-depth description of the reason.
        prefix: Whether the detail should be prefixed by the peppy signature.
            Defaults to True.
        from_id: The ID of the user who banned the user.
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
    remove_from_leaderboard(user_id)

    insert_ban_log(user_id, summary, detail, prefix, from_id)


def ban_with_log(
    user_id: int,
    summary: str,
    detail: str,
    prefix: bool = True,
    from_id: Optional[int] = None,
) -> None:
    """Ban the user alongside inserting a log into the database.

    Args:
        user_id: The ID of the user to assign the log to.
        summary: A short description of the reason.
        detail: A more detailed, in-depth description of the reason.
        prefix: Whether the detail should be prefixed by the peppy signature.
            Defaults to True.
        from_id: The ID of the user who banned the user.
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
    remove_from_leaderboard(user_id)

    insert_ban_log(user_id, summary, detail, prefix, from_id)
