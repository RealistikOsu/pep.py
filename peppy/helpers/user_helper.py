from __future__ import annotations

import bcrypt
from objects import glob


def username_safe(s: str) -> str:
    """Returns safe to use username."""

    return s.lower().strip().replace(" ", "_")


def verify_password(user_id: int, password: str) -> bool:
    """Verifies if the provided username + password combination is correct,
    providing a cache to ensure speed with bcrypt.

    Note:
        This only supports Ripple Password v2 (MD5 + BCrypt) as no one in
            their right mind should be using v1.

    Args:
        user_id (int): The ID of the user within the database.
        password (str): The user's password hashed with MD5.
    """

    passw_db = glob.db.fetch(
        "SELECT password_md5 FROM users WHERE id = %s LIMIT 1",
        (user_id,),
    )["password_md5"]

    # Check if we already cached them, for speed benefit.
    if passw_db in glob.cached_passwords:
        return glob.cached_passwords[passw_db] == password

    res = bcrypt.checkpw(password.encode(), passw_db.encode())
    # Cache it for later
    if res:
        glob.cached_passwords[passw_db] = password

    return res


def get_country(user_id: int) -> str:
    """Returns the country of the user.

    Args:
        user_id (int): The ID of the user within the database.
    """

    return glob.db.fetch(
        "SELECT country FROM users WHERE id = %s LIMIT 1",
        (user_id,),
    )["country"]


def set_country(user_id: int, country_code: str) -> None:
    """Sets the country for a specific user to `country_code`.

    Args:
        user_id (int): The user ID for the user.
        country_code (str): The 2 letter country code to set.
    """

    country_code = country_code.upper()

    glob.db.execute(
        "UPDATE users SET country = %s WHERE id = %s LIMIT 1",
        (country_code, user_id),
    )
