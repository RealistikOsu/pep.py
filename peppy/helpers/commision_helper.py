from __future__ import annotations

from typing import Optional

from objects import glob
from helpers import chatHelper as chat


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

    # Send message to user
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
        )
    )
