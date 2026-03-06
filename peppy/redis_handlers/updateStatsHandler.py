from __future__ import annotations

from common.redis import generalPubSubHandler
from objects import glob
from helpers import commission_helper
from logger import error


class handler(generalPubSubHandler.generalPubSubHandler):
    def __init__(self):
        super().__init__()
        self.type = "int"

    def handle(self, userID):
        userID = super().parseData(userID)
        if userID is None:
            return
        targetToken = glob.tokens.getTokenFromUserID(userID)
        if targetToken is not None:
            try:
                targetToken.updateCachedStats()
            except Exception as e:
                error(
                    "Failed to update cached stats in updateStatsHandler",
                    extra={"user_id": userID, "error": str(e)},
                )
                return
            try:
                commission_helper.update_commission_progress(userID)
            except Exception as e:
                error(
                    "Failed to update commission progress in updateStatsHandler",
                    extra={"user_id": userID, "error": str(e)},
                )
