from __future__ import annotations

from common.constants import bcolors as bcolours  # :trolley:


def printServerStartHeader(asciiArt: bool = True):
    """
    Print server start message

    :param asciiArt: print BanchoBoat ascii art. Default: True
    :return:
    """
    if asciiArt:
        print_coloured(
            r""" ______   ______   ______       ______   __  __
/_____/\ /_____/\ /_____/\     /_____/\ /_/\/_/\
\:::_ \ \\::::_\/_\:::_ \ \    \:::_ \ \\ \ \ \ \
 \:(_) \ \\:\/___/\\:(_) \ \ ___\:(_) \ \\:\_\ \ \
  \: ___\/ \::___\/_\: ___\//__/\\: ___\/ \::::_\/
   \ \ \    \:\____/\\ \ \  \::\ \\ \ \     \::\ \
    \_\/     \_____\/ \_\/   \:_\/ \_\/      \__\/ """,
            bcolours.GREEN,
        )

    print_coloured(f"# pep.py - The RealistikOsu Bancho emulator.", bcolours.BLUE)
    print_coloured(
        f"# This is a fork of the now deprecated pep.py by the Ripple Team.",
        bcolours.BLUE,
    )


def print_coloured(string: str, colour: str):
    """
    Print a colored string

    :param string: string to print
    :param color: ANSI color code
    :return:
    """
    print(colour + string + bcolours.ENDC)
