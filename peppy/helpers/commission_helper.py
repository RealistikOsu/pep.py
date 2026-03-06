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


def award_coins(user_id: int, quantity: int) -> int:
    """Atomic coin increment. Returns new balance."""
    glob.db.execute(
        "UPDATE users SET coins = coins + %s WHERE id = %s",
        (quantity, user_id),
    )
    return get_current_coins(user_id) or 0


AWARD_MESSAGE_TEMPLATE = (
    "You have been awarded {coin_quantity} (total {new_quantity}) coins for {reason}."
)


def handle_award_coins_routine(
    user_id: int,
    coin_quantity: int,
    reason: str,
) -> None:
    new_quantity = award_coins(user_id, coin_quantity)

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
    tables = {
        "users_stats": ["std", "taiko", "ctb", "mania"],
        "rx_stats": ["std", "taiko", "ctb"],
        "ap_stats": ["std"]
    }
    stats_to_sum = ["playcount", "total_score", "ranked_score", "pp", "playtime"]

    total_stats = {s: 0 for s in stats_to_sum}

    for table, modes in tables.items():
        cols = [f"{s}_{m}" for s in stats_to_sum for m in modes]
        
        row = glob.db.fetch(f"SELECT {', '.join(cols)} FROM {table} WHERE id = %s", (user_id,))
        
        if row:
            for s in stats_to_sum:
                for m in modes:
                    val = row.get(f"{s}_{m}")
                    if val:
                        total_stats[s] += int(val)
    
    return total_stats


def assign_daily_commissions(user_id: int) -> bool:
    """Assign 4 random commissions. Returns True if newly assigned."""
    today = date.today()

    existing = glob.db.fetchAll(
        "SELECT id FROM user_commissions WHERE user_id = %s AND date = %s",
        (user_id, today),
    )
    if existing:
        return False

    templates = glob.db.fetchAll("SELECT * FROM commission_templates")
    if not templates:
        return False

    chosen = random.sample(templates, min(4, len(templates)))
    stats = get_total_stats(user_id)

    any_inserted = False
    for t in chosen:
        start_value = stats.get(t["type"], 0)

        # INSERT IGNORE to prevent race condition errors
        res = glob.db.execute(
            "INSERT IGNORE INTO user_commissions (user_id, name, description, type, goal, reward, start_value, date) "
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
        if res > 0:
            any_inserted = True

    if any_inserted:
        update_commission_progress(user_id)
        return True
    
    return False


def update_commission_progress(user_id: int) -> None:
    today = date.today()
    commissions = glob.db.fetchAll(
        "SELECT * FROM user_commissions WHERE user_id = %s AND date = %s AND completed = 0",
        (user_id, today),
    )

    if not commissions:
        return

    stats = get_total_stats(user_id)

    last_score_acc = 0
    score_tables = ["scores", "scores_relax", "scores_ap"]
    for table in score_tables:
        res = glob.db.fetch(
            f"SELECT accuracy FROM {table} WHERE userid = %s AND completed = 3 AND DATE(FROM_UNIXTIME(time)) = %s ORDER BY id DESC LIMIT 1",
            (user_id, today),
        )
        if res and res["accuracy"] > last_score_acc:
            last_score_acc = res["accuracy"]

    for comm in commissions:
        progress = 0
        if comm["type"] in stats:
            progress = max(0, stats[comm["type"]] - comm["start_value"])
            if comm["type"] == "playtime":
                progress //= 60
        elif comm["type"] == "accuracy":
            any_map_met_goal = False
            for table in score_tables:
                res = glob.db.fetch(
                    f"SELECT id FROM {table} WHERE userid = %s AND completed = 3 AND accuracy >= %s AND DATE(FROM_UNIXTIME(time)) = %s LIMIT 1",
                    (user_id, comm["goal"], today),
                )
                if res:
                    any_map_met_goal = True
                    break
            
            if any_map_met_goal:
                progress = comm["goal"]
        elif comm["type"] == "login":
            progress = 1

        if progress >= comm["goal"]:
            glob.db.execute(
                "UPDATE user_commissions SET progress = %s, completed = 1 WHERE id = %s AND completed = 0",
                (comm["goal"], comm["id"]),
            )
            
            # Atomic claim check
            claim_id = glob.db.execute(
                "INSERT IGNORE INTO user_commission_claims (commission_id) VALUES (%s)",
                (comm["id"],),
            )
            
            if claim_id > 0:
                handle_award_coins_routine(
                    user_id,
                    comm["reward"],
                    f"completing commission: {comm['name']}",
                )
        else:
            glob.db.execute(
                "UPDATE user_commissions SET progress = %s WHERE id = %s AND completed = 0",
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
        # Atomic claim for bonus
        # (Using rowcount/lastrowid would be better, but INSERT IGNORE on PK (user_id, date) is sufficient 
        # as it won't raise error, and we can check if it was newly inserted if we had cursor access.)
        # Since DatabasePool returns lastrowid, and PK is not AUTO_INCREMENT, it might return 0.
        # Let's use a separate claim table for bonus too if we want to be 100% sure.
        
        glob.db.execute(
            "INSERT IGNORE INTO user_daily_bonus (user_id, date, claimed) VALUES (%s, %s, 1)",
            (user_id, today),
        )
        
        # To be safe without changing DatabasePool:
        # Use user_commission_claims with a special key for daily bonus
        # e.g., negative ID or separate table. I'll use a separate table for bonus claims.
        
        bonus_claim_id = glob.db.execute(
            "INSERT IGNORE INTO user_daily_bonus_claims (user_id, date) VALUES (%s, %s)",
            (user_id, today),
        )
        
        if bonus_claim_id > 0:
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
    assign_daily_commissions(user_id)
    commissions = glob.db.fetchAll(
        "SELECT * FROM user_commissions WHERE user_id = %s AND date = %s",
        (user_id, today),
    )

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
