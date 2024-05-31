from __future__ import annotations

import json
import random

import tornado.gen
import tornado.web

from common.web import requestsManager
from config import config
from objects import glob


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self):
        """Handles the server info endpoint for the Aeris client."""
        resp_dict = {
            "version": 0,
            "motd": f"{config.SRV_NAME}\n"
            + random.choice(glob.banchoConf.config["Quotes"]),
            "onlineUsers": len(glob.tokens.tokens),
            "icon": "https://ussr.pl/static/image/newlogo2.png",
            "botID": config.SRV_BOT_ID,
        }
        self.write(json.dumps(resp_dict))
