from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Optional

from objects import glob


@dataclass
class UserStatus:
    """Dataclass storing the data for a user status."""

    id: int
    user_id: int
    status: str
    enabled: bool

    def insert(self) -> None:
        """Inserts the status into the database and cache, overwriting it if one already
        exists. Also sets `id` attribute to lastrowid."""

        self.id = glob.db.execute(
            """
INSERT INTO user_statuses (user_id, status, enabled) VALUES (%(userid)s, %(status)s, %(enabled)s)
ON DUPLICATE KEY
UPDATE status = %(status)s, enabled = %(enabled)s
        """,
            {
                "userid": self.user_id,
                "status": self.status,
                "enabled": int(
                    self.enabled,
                ),  # Tried formatting with %d but this sql conn is cursed
            },
        )
        glob.user_statuses.insert(self)

    @staticmethod
    def from_db(db_d: dict[str, Any]) -> UserStatus:
        """Creates an instance of `UserStatus` from a db dictionary."""

        db_d["enabled"] = bool(db_d["enabled"])
        return UserStatus(
            **db_d,
        )


class StatusManager:
    """A manager class soring all user statuses."""

    __slots__ = ("_repo",)

    def __init__(self) -> None:
        self._repo: dict[int, UserStatus] = {}

    def __len__(self) -> int:
        return len(self._repo)

    def insert(self, status: UserStatus) -> None:
        """Inserts a user status if one already exists."""

        self._repo[status.user_id] = status

    def get_status(self, user_id: int) -> Optional[UserStatus]:
        """Attempts to fetch a status for a user from the cached repo.
        Returns None if not cached."""

        return self._repo.get(user_id)

    def get_status_if_enabled(self, user_id: int) -> Optional[UserStatus]:
        """Attempts to fetch a status for a user from the cached repo.
        Returns if exists and the status is enabled. Else None."""

        if st := self.get_status(user_id):
            if st.enabled:
                return st

    def load_from_db(self) -> int:
        """Loads all statuses from the database. Returns amount of scores added."""

        res = glob.db.fetchAll("SELECT * FROM user_statuses")

        for status in res:
            self.insert(UserStatus.from_db(status))

        return len(res)
