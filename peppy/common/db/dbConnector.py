from __future__ import annotations

import queue
import time
from typing import Any
from typing import Optional

import MySQLdb
from MySQLdb.connections import Connection

from logger import log


class Worker:
    """
    A single MySQL worker
    """

    __slots__ = (
        "connection",
        "temporary",
    )

    def __init__(self, connection: Connection, temporary: bool = False) -> None:
        """
        Initialize a MySQL worker

        :param connection: database connection object
        :param temporary: if True, this worker will be flagged as temporary
        """
        self.connection = connection
        self.temporary = temporary
        log.debug(f"Created MySQL worker. Temporary: {self.temporary}")

    def __del__(self) -> None:
        """
        Close connection to the server

        :return:
        """
        self.connection.close()


class ConnectionPool:
    """
    A MySQL workers pool
    """

    __slots__ = (
        "config",
        "maxSize",
        "pool",
        "consecutiveEmptyPool",
    )

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        database: str,
        size: int = 128,
    ) -> None:
        """
        Initialize a MySQL connections pool

        :param host: MySQL host
        :param username: MySQL username
        :param password: MySQL password
        :param database: MySQL database name
        :param size: pool max size
        """
        self.config = (host, username, password, database)
        self.maxSize = size
        self.pool = queue.Queue(self.maxSize)
        self.consecutiveEmptyPool = 0
        self.fillPool()

    def newWorker(self, temporary: bool = False) -> Worker:
        """
        Create a new worker.

        :param temporary: if True, flag the worker as temporary
        :return: instance of worker class
        """
        db = MySQLdb.connect(
            *self.config, autocommit=True, charset="utf8", use_unicode=True
        )
        conn = Worker(db, temporary)
        return conn

    def fillPool(self, newConnections: int = 0) -> None:
        """
        Fill the queue with workers

        :param newConnections:    number of new connections. If 0, the pool will be filled entirely.
        :return:
        """
        # If newConnections = 0, fill the whole pool
        if newConnections == 0:
            newConnections = self.maxSize

        # Fill the pool
        for _ in range(0, newConnections):
            if not self.pool.full():
                self.pool.put_nowait(self.newWorker())

    def getWorker(self) -> Worker:
        """
        Get a MySQL connection worker from the pool.
        If the pool is empty, a new temporary worker is created.

        :param level: number of failed connection attempts. If > 50, return None
        :return: instance of worker class
        """

        try:
            if self.pool.empty():
                # The pool is empty. Spawn a new temporary worker
                log.warning("MySQL connections pool is empty. Using temporary worker.")
                worker = self.newWorker(True)

                # Increment saturation
                self.consecutiveEmptyPool += 1

                # If the pool is usually empty, expand it
                if self.consecutiveEmptyPool >= 10:
                    log.warning(
                        "MySQL connections pool is empty. Filling connections pool.",
                    )
                    self.fillPool()
            else:
                # The pool is not empty. Get worker from the pool
                # and reset saturation counter
                worker = self.pool.get()
                self.consecutiveEmptyPool = 0
        except MySQLdb.OperationalError:
            # Connection to server lost
            # Wait 1 second and try again
            log.warning("Can't connect to MySQL database. Retrying in 1 second...")
            time.sleep(1)
            return self.getWorker()

        # Return the connection
        return worker

    def putWorker(self, worker: Worker):
        """
        Put the worker back in the pool.
        If the worker is temporary, close the connection
        and destroy the object

        :param worker: worker object
        :return:
        """
        if worker.temporary or self.pool.full():
            # Kill the worker if it's temporary or the queue
            # is full and we can't  put anything in it
            del worker
        else:
            # Put the connection in the queue if there's space
            self.pool.put_nowait(worker)


class DatabasePool:
    """
    A MySQL helper with multiple workers
    """

    __slots__ = ("pool",)

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        database: str,
        initialSize: int,
    ) -> None:
        """
        Initialize a new MySQL database helper with multiple workers.
        This class is thread safe.

        :param host: MySQL host
        :param username: MySQL username
        :param password: MySQL password
        :param database: MySQL database name
        :param initialSize: initial pool size
        """
        self.pool = ConnectionPool(host, username, password, database, initialSize)

    def execute(self, query: str, params: object = ()) -> int:
        """
        Executes a query

        :param query: query to execute. You can bind parameters with %s
        :param params: parameters list. First element replaces first %s and so on
        """
        cursor = None
        worker = self.pool.getWorker()
        if worker is None:
            return 0
        try:
            # Create cursor, execute query and commit
            cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(query, params)
            log.debug(query)
            return cursor.lastrowid
        finally:
            # Close the cursor and release worker's lock
            if cursor is not None:
                cursor.close()
            if worker is not None:
                self.pool.putWorker(worker)

    def fetch(self, query: str, params: object = ()) -> Optional[dict[str, Any]]:
        """
        Fetch a single value from db that matches given query

        :param query: query to execute. You can bind parameters with %s
        :param params: parameters list. First element replaces first %s and so on
        """
        cursor = None
        worker = self.pool.getWorker()
        if worker is None:
            return None
        try:
            # Create cursor, execute the query and fetch one/all result(s)
            cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(query, params)
            log.debug(query)
            return cursor.fetchone()
        finally:
            # Close the cursor and release worker's lock
            if cursor is not None:
                cursor.close()
            if worker is not None:
                self.pool.putWorker(worker)

    def fetchAll(self, query: str, params: object = ()) -> list[dict[str, Any]]:
        """
        Fetch all values from db that matche given query.
        Calls self.fetch with all = True.

        :param query: query to execute. You can bind parameters with %s
        :param params: parameters list. First element replaces first %s and so on
        """

        cursor = None
        worker = self.pool.getWorker()
        if worker is None:
            return []
        try:
            # Create cursor, execute the query and fetch one/all result(s)
            cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(query, params)
            log.debug(query)
            return cursor.fetchall()
        finally:
            # Close the cursor and release worker's lock
            if cursor is not None:
                cursor.close()
            if worker is not None:
                self.pool.putWorker(worker)
