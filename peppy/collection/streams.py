from __future__ import annotations

from typing import Optional
from typing import TYPE_CHECKING

from objects import glob
from objects.stream import Stream

if TYPE_CHECKING:
    from objects.osuToken import UserToken

# TODO: use *args and **kwargs
class StreamList:
    def __init__(self):
        self.streams: dict[str, Stream] = {}

    def add(self, name: str) -> Stream:
        """
        Create a new stream list if it doesn't already exist

        :param name: stream name
        :return: The stream object.
        """
        if name not in self.streams:
            self.streams[name] = Stream(name)

    def remove(self, name: str) -> bool:
        """
        Removes an existing stream and kick every user in it

        :param name: stream name
        :return: Whether a stream actually got nuked
        """
        if name in self.streams:
            for i in self.streams[name].clients:
                if t := glob.tokens.tokens.get(i):
                    t.leaveStream(name)
            self.streams.pop(name)
            return True

        return False

    def join(
        self,
        streamName: str,
        client: Optional[UserToken] = None,
        token: Optional[str] = None,
    ):
        """
        Add a client to a stream

        :param streamName: stream name
        :param client: client (osuToken) object
        :param token: client uuid string
        :return:
        """
        if streamName not in self.streams:
            return
        self.streams[streamName].addClient(client=client, token=token)

    def leave(
        self,
        streamName: str,
        client: Optional[UserToken] = None,
        token: Optional[str] = None,
    ):
        """
        Remove a client from a stream

        :param streamName: stream name
        :param client: client (osuToken) object
        :param token: client uuid string
        :return:
        """
        if streamName not in self.streams:
            return
        self.streams[streamName].removeClient(client=client, token=token)

    def broadcast(
        self,
        streamName: str,
        data: bytes,
        but: Optional[list[str]] = None,
    ) -> None:
        """
        Send some data to all clients in a stream

        :param streamName: stream name
        :param data: data to send
        :param but: array of tokens to ignore. Default: None (send to everyone)
        :return:
        """
        if streamName not in self.streams:
            return
        self.streams[streamName].broadcast(data, but)

    def dispose(self, streamName: str) -> None:
        """
        Call `dispose` on `streamName`

        :param streamName: name of the stream
        :param args:
        :param kwargs:
        :return:
        """
        if streamName not in self.streams:
            return
        self.streams[streamName].dispose()

    def getStream(self, streamName: str) -> Optional[Stream]:
        """
        Returns streamName's stream object or None if it doesn't exist

        :param streamName:
        :return:
        """
        if streamName in self.streams:
            return self.streams[streamName]
        return None
