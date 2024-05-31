from __future__ import annotations

from common.redis import generalPubSubHandler
from helpers import chatHelper
from objects import glob

# Handles `peppy:bot_msg`
class handler(generalPubSubHandler.generalPubSubHandler):
    def __init__(self):
        super().__init__()
        self.structure = {"to": "", "message": ""}

    def handle(self, data):
        handler_data = super().parseData(data)
        if handler_data is None:
            return

        chatHelper.sendMessage(
            fro=glob.BOT_NAME,
            to=handler_data["to"].encode("latin-1").decode("utf-8"),
            message=handler_data["message"].encode("latin-1").decode("utf-8"),
        )
