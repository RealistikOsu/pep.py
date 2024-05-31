from __future__ import annotations

from typing import Optional

import tornado.gen
import tornado.web
from tornado.ioloop import IOLoop

from config import config
from logger import log
from objects import glob


class asyncRequestHandler(tornado.web.RequestHandler):
    """
    Tornado asynchronous request handler
    create a class that extends this one (requestHelper.asyncRequestHandler)
    use asyncGet() and asyncPost() instead of get() and post().
    Done. I'm not kidding.
    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, *args, **kwargs):
        try:
            yield tornado.gen.Task(
                runBackground,
                (self.asyncGet, tuple(args), dict(kwargs)),
            )
        finally:
            if not self._finished:
                self.finish()

    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self, *args, **kwargs):
        try:
            yield tornado.gen.Task(
                runBackground,
                (self.asyncPost, tuple(args), dict(kwargs)),
            )
        finally:
            if not self._finished:
                self.finish()

    def asyncGet(self, *args, **kwargs) -> None:
        self.send_error(405)

    def asyncPost(self, *args, **kwargs) -> None:
        self.send_error(405)

    def getRequestIP(self) -> Optional[str]:
        """
        If the server is configured to use Cloudflare, returns the `CF-Connecting-IP` header.
        Otherwise, returns the `X-Real-IP` header.

        :return: Client IP address
        """

        # Check if they are connecting through a switcher
        if "ppy.sh" in self.request.headers.get("Host", "") or not config.USING_CF:
            return self.request.headers.get("X-Real-IP")

        return self.request.headers.get("CF-Connecting-IP")


def runBackground(data, callback):
    """
    Run a function in the background.
    Used to handle multiple requests at the same time

    :param data: (func, args, kwargs)
    :param callback: function to call when `func` (data[0]) returns
    :return:
    """
    func, args, kwargs = data

    def _callback(result):
        IOLoop.instance().add_callback(lambda: callback(result))

    glob.pool.apply_async(func, args, kwargs, _callback)


def checkArguments(arguments, requiredArguments):
    """
    Check that every requiredArguments elements are in arguments

    :param arguments: full argument list, from tornado
    :param requiredArguments: required arguments list
    :return: True if all arguments are passed, False if not
    """
    for i in requiredArguments:
        if i not in arguments:
            return False
    return True


def printArguments(t):
    """
    Print passed arguments, for debug purposes

    :param t: tornado object (self)
    """
    msg = "ARGS::"
    for i in t.request.arguments:
        msg += f"{i}={t.get_argument(i)}\r\n"
    log.debug(msg)
