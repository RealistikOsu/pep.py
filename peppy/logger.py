from __future__ import annotations

import sys
import time

from colorama import Back
from colorama import Fore

CLEAR_FORE = Fore.RESET
CLEAR_BACK = Back.RESET

# Received permission directly from him to use it. Just figured it looks cool.
# Made some optimisations to it.
__name__ = "LoggerModule"
__author__ = "Lenforiee"

DEBUG = "debug" in sys.argv


def formatted_date():
    """Returns the current fromatted date in the format
    DD/MM/YYYY HH:MM:SS"""

    return time.strftime("%d-%m-%Y %H:%M:%S", time.localtime())


def log_message(content: str, l_type: str, bg_col: Fore):
    """Creates the final string and writes it to console.

    Args:
        content (str): The main text to be logged to
            console.
        l_type (str): The type of the log that will be
            displayed to the user.
        bl_col (Fore): The background colour for the
            `l_type`.
    """

    # Print to console. Use this as faster ig.
    sys.stdout.write(
        f"{Fore.WHITE}{bg_col}[{l_type}]{CLEAR_BACK} - "
        f"[{formatted_date()}] {content}{CLEAR_FORE}\n",
    )


class Logger:
    def debug(self, message: str):
        if DEBUG:
            return log_message(message, "DEBUG", Back.YELLOW)

    def info(self, message: str):
        return log_message(message, "INFO", Back.GREEN)

    def error(self, message: str):
        return log_message(message, "ERROR", Back.RED)

    def warning(self, message: str):
        return log_message(message, "WARNING", Back.BLUE)

    # Ripple Stuff
    def logMessage(
        self,
        message,
        alertType="INFO",
        messageColor=Back.BLACK,
        discord=None,
        alertDev=False,
        of=None,
        stdout=True,
    ):
        if stdout:
            log_message(message, alertType, messageColor)

    def chat(self, message: str):
        self.debug(f"User sent public message: {message}")

    def pm(self, message: str):
        pass

    def rap(self, userID, message, discord=False, through=None):
        log_message(f"{userID} {message}", "RAP", Back.GREEN)


log = Logger()
