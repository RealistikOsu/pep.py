from __future__ import annotations

import os
import time
from typing import Union

# Orjson is optional and can be replaced 1:1 by the default one. Only use
# it when we have it.
try:
    from orjson import dump as j_dump
except ImportError:
    from json import dump as j_dump
try:
    from orjson import load as j_load
except ImportError:
    from json import load as j_load


class JsonFile:
    """Assists within working with simple JSON files."""

    def __init__(self, file_name: str, load: bool = True):
        """Loads a Json file `file_name` from disk.

        Args:
            file_name (str): The path including the filename of the JSON file
                you would like to load.
            load (str): Whether the JSON file should be loaded immidiately on
                object creation.
        """

        self.file = None
        self.file_name = file_name
        if load and os.path.exists(file_name):
            self.load_file()

    def load_file(self) -> None:
        """Reloads the file fully into memory."""

        with open(self.file_name) as f:
            self.file = j_load(f)

    def get_file(self) -> dict:
        """Returns the loaded JSON file as a dict.

        Returns:
            Contents of the file.
        """
        return self.file

    def write_file(self, new_content: Union[dict, list]) -> None:
        """Writes `new_content` to the target file.

        Args:
            new_content (dict, list): The new content that should be placed
                within the file.
        """

        with open(self.file_name, "w") as f:
            j_dump(new_content, f, indent=4)
        self.file = new_content


class Timer:
    """A simple timer class used to time the execution of code."""

    def __init__(self):
        """Initialises timer for use."""
        self.start_time = 0
        self.end_time = 0

    def start(self) -> None:
        """Begins the timer."""
        self.start_time = time.time()

    def end(self) -> float:
        """Ends the timer and returns final time."""
        self.end_time = time.time()
        return self.end_time - self.start_time

    def get_difference(self) -> float:
        """Returns the difference between start and end"""
        return self.end_time - self.start_time

    def reset(self) -> None:
        """Resets the timer."""
        self.end_time = 0
        self.start_time = 0

    def ms_return(self) -> float:
        """Returns difference in 2dp ms."""
        return round((self.end_time - self.start_time) * 1000, 2)

    def end_time_str(self) -> str:
        self.end()
        return self.time_str()

    def time_str(self) -> str:
        """Returns a nicely formatted timing result."""

        # This function already takes a timer so its a match in heaven lmfao.
        return time_str(self)


def time_str(timer: Timer) -> str:
    """If time is in ms, returns ms value. Else returns rounded seconds value."""
    time = timer.end()
    if time < 1:
        time_str = f"{timer.ms_return()}ms"
    else:
        time_str = f"{round(time,2)}s"
    return time_str
