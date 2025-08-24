from __future__ import annotations

from common.redis import generalPubSubHandler
from objects import glob
from packets import server


class handler(generalPubSubHandler.generalPubSubHandler):
    def __init__(self):
        super().__init__()
        self.structure = {"userID": 0, "message": ""}

    def handle(self, data):
        data = super().parseData(data)
        if data is None:
            return
        targetToken = glob.tokens.getTokenFromUserID(data["userID"])
        if targetToken is not None:
            targetToken.enqueue(server.notification(data["message"]))
