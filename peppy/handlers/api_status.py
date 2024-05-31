from __future__ import annotations

import json

import tornado.gen
import tornado.web

from common.web import requestsManager
from logger import log
from objects import glob


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self, user_id: int):
        token = glob.tokens.getTokenFromUserID(user_id)

        if not token:
            self.set_status(204)
            return

        return self.write(
            json.dumps(
                {
                    "code": 200,
                    "username": token.username,
                    "user_id": token.userID,
                    "privileges": token.privileges,
                    "action": {
                        "id": token.actionID,
                        "text": token.actionText,
                        "beatmap": {
                            "id": token.beatmapID,
                            "md5": token.actionMd5,
                            "mods": token.actionMods,
                        },
                    },
                    "match_id": token.matchID,
                    "mode": token.gameMode,
                    "rank": token.gameRank,
                    "autopilot": token.autopiloting,
                    "relax": token.relaxing,
                },
            ),
        )
