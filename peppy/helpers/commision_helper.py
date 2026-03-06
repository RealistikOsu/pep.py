from __future__ import annotations

import random
from datetime import date
from typing import Any
from typing import Optional

from helpers import chatHelper as chat
from objects import glob


def get_current_coins(user_id: int) -> Optional[int]:
    user_coins = glob.db.fetch(
        "SELECT coins FROM users WHERE id = %s",
        (user_id,),
    )

    if user_coins is None:
        return None

    return user_coins["coins"]


def set_coins(user_id: int, coins: int) -> None:
    glob.db.execute(
        "UPDATE users SET coins = %s WHERE id = %s",
        (coins, user_id),
    )


AWARD_MESSAGE_TEMPLATE = (
    "You have been awarded {coin_quantity} (total {new_quantity}) coins for {reason}."
)


def handle_award_coins_routine(
    user_id: int,
    coin_quantity: int,
    reason: str,
) -> None:
    current_coins = get_current_coins(user_id)

    if current_coins is None:
        return

    new_quantity = current_coins + coin_quantity
    set_coins(user_id, new_quantity)

    user = glob.tokens.getTokenFromUserID(user_id)
    if user is None:
        return

    chat.sendMessage(
        glob.BOT_NAME,
        token=user,
        message=AWARD_MESSAGE_TEMPLATE.format(
            coin_quantity=coin_quantity,
            new_quantity=new_quantity,
            reason=reason,
        ),
    )


def get_total_stats(user_id: int) -> dict[str, int]:
    """Get summed stats across all modes and sub-modes."""
    tables = ["users_stats", "rx_stats", "ap_stats"]
    modes = ["std", "taiko", "ctb", "mania"]
    stats_to_sum = ["playcount", "total_score", "ranked_score", "pp", "playtime"]

    total_stats = {s: 0 for s in stats_to_sum}

    for table in tables:
        # Check if table exists (ap_stats might not have all modes, etc.)
        # But we'll just try to fetch and sum.
        # Construct the query for all 4 modes in one go for efficiency.
        cols = []
        for s in stats_to_sum:
            for m in modes:
                cols.append(f"SUM({s}_{m}) as {s}_{m}")
        
        # Actually, SUM() over multiple columns in one row doesn't make sense,
        # we just want to sum the columns for this specific user.
        cols = []
        for s in stats_to_sum:
            for m in modes:
                cols.append(f"{s}_{m}")
        
        query = f"SELECT {', '.join(cols)} FROM {table} WHERE id = %s"
        row = glob.db.fetch(query, (user_id,))
        
        if row:
            for s in stats_to_sum:
                for m in modes:
                    val = row.get(f"{s}_{m}")
                    if val:
                        total_stats[s] += int(val)
    
    return total_stats


def assign_daily_commissions(user_id: int) -> list[dict[str, Any]]:
    today = date.today()

    existing = glob.db.fetchAll(
        "SELECT * FROM user_commissions WHERE user_id = %s AND date = %s",
        (user_id, today),
    )
    if existing:
        return existing

    templates = glob.db.fetchAll("SELECT * FROM commission_templates")
    if not templates:
        return []

    chosen = random.sample(templates, min(4, len(templates)))
    stats = get_total_stats(user_id)

    for t in chosen:
        start_value = stats.get(t["type"], 0)

        glob.db.execute(
            "INSERT INTO user_commissions (user_id, name, description, type, goal, reward, start_value, date) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                user_id,
                t["name"],
                t["description"].format(goal=t["goal"]),
                t["type"],
                t["goal"],
                t["reward"],
                start_value,
                today,
            ),
        )

    update_commission_progress(user_id)

    return glob.db.fetchAll(
        "SELECT * FROM user_commissions WHERE user_id = %s AND date = %s",
        (user_id, today),
    )


def update_commission_progress(user_id: int) -> None:
    today = date.today()
    commissions = glob.db.fetchAll(
        "SELECT * FROM user_commissions WHERE user_id = %s AND date = %s AND completed = 0",
        (user_id, today),
    )

    if not commissions:
        return

    stats = get_total_stats(user_id)

    # Check accuracy across all score tables
    last_score_acc = 0
    score_tables = ["scores", "scores_relax", "scores_ap"]
    for table in score_tables:
        res = glob.db.fetch(
            f"SELECT accuracy FROM {table} WHERE userid = %s ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        if res and res["accuracy"] > last_score_acc:
            last_score_acc = res["accuracy"]

    for comm in commissions:
        progress = 0
        if comm["type"] in stats:
            progress = stats[comm["type"]] - comm["start_value"]
            if comm["type"] == "playtime":
                progress //= 60 # Seconds to minutes
        elif comm["type"] == "accuracy":
            if last_score_acc >= comm["goal"]:
                progress = comm["goal"]
        elif comm["type"] == "login":
            progress = 1

        if progress >= comm["goal"]:
            glob.db.execute(
                "UPDATE user_commissions SET progress = %s, completed = 1 WHERE id = %s",
                (comm["goal"], comm["id"]),
            )
            handle_award_coins_routine(
                user_id,
                comm["reward"],
                f"completing commission: {comm['name']}",
            )
        else:
            glob.db.execute(
                "UPDATE user_commissions SET progress = %s WHERE id = %s",
                (progress, comm["id"]),
            )

    check_daily_bonus(user_id)


def check_daily_bonus(user_id: int) -> None:
    today = date.today()

    bonus = glob.db.fetch(
        "SELECT * FROM user_daily_bonus WHERE user_id = %s AND date = %s",
        (user_id, today),
    )
    if bonus:
        return

    completed_count = glob.db.fetch(
        "SELECT COUNT(*) as count FROM user_commissions WHERE user_id = %s AND date = %s AND completed = 1",
        (user_id, today),
    )["count"]

    if completed_count >= 4:
        bonus_reward = 20
        glob.db.execute(
            "INSERT INTO user_daily_bonus (user_id, date, claimed) VALUES (%s, %s, 1)",
            (user_id, today),
        )
        handle_award_coins_routine(
            user_id,
            bonus_reward,
            "completing all daily commissions",
        )
        
        user = glob.tokens.getTokenFromUserID(user_id)
        if user:
            chat.sendMessage(
                glob.BOT_NAME,
                token=user,
                message="Congratulations! You've completed all daily commissions and received a bonus reward!",
            )


def get_commission_status(user_id: int) -> str:
    today = date.today()
    commissions = assign_daily_commissions(user_id)

    status = [f"--- Daily Commissions for {today} ---"]
    for i, comm in enumerate(commissions, 1):
        check = "X" if comm["completed"] else " "
        status.append(
            f"{i}. [{check}] {comm['name']}: {comm['progress']}/{comm['goal']} ({comm['description']})",
        )

    bonus = glob.db.fetch(
        "SELECT * FROM user_daily_bonus WHERE user_id = %s AND date = %s",
        (user_id, today),
    )
    bonus_check = "X" if bonus else " "
    status.append(f"Bonus: [{bonus_check}] All daily commissions completed")

    return "\n".join(status)
