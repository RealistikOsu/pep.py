from __future__ import annotations

from common.redis import generalPubSubHandler
from objects import glob
from helpers import commission_helper


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
            targetToken.updateCachedStats()
            commission_helper.update_commission_progress(userID)
