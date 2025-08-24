from __future__ import annotations

from typing import Optional
from typing import TYPE_CHECKING

from objects import glob
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from objects.osuToken import UserToken


class Stream:
    def __init__(self, name):
        """
        Initialize a stream object

        :param name: stream name
        """
        self.name = name
        self.clients: list[str] = []

    def addClient(
        self,
        client: Optional[UserToken] = None,
        token: Optional[str] = None,
    ) -> bool:
        """
        Add a client to this stream if not already in

        :param client: client (UserToken) object
        :param token: client uuid string
        :return: Bool of success
        """
        if client is None and token is None:
            return False
        if client is not None:
            token = client.token
        if token not in self.clients:
            logger.info(
                "Token joined stream", extra={"token": token, "stream": self.name},
            )
            self.clients.append(token)
            return True

        return False

    def removeClient(
        self,
        client: Optional[UserToken] = None,
        token: Optional[str] = None,
    ):
        """
        Remove a client from this stream if in

        :param client: client (osuToken) object
        :param token: client uuid string
        :return:
        """
        if client is None and token is None:
            return
        if client is not None:
            token = client.token
        if token in self.clients:
            logger.info(
                "Token left stream", extra={"token": token, "stream": self.name},
            )
            self.clients.remove(token)

    def broadcast(self, data: bytes, but: Optional[list[str]] = None) -> None:
        """
        Send some data to all (or some) clients connected to this stream

        :param data: data to send
        :param but: array of tokens to ignore. Default: None (send to everyone)
        :return:
        """
        if but is None:
            but = []
        for token_str in self.clients:
            token = glob.tokens.tokens.get(token_str)
            if token and token.token not in but:
                token.enqueue(data)

    def dispose(self) -> None:
        """
        Tell every client in this stream to leave the stream

        :return:
        """
        for i in self.clients:
            token = glob.tokens.tokens.get(i)
            if token:
                token.leaveStream(self.name)
