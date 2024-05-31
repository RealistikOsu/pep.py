# pep.py
The RealistikOsu realtime server!

![image](https://user-images.githubusercontent.com/36131887/118535385-4fd4c200-b742-11eb-8886-7ba8463b8d57.png)

## What does it do?
This portion of the RealistikOsu manages all of the real-time, packet related portions of the Bancho protocol. This includes but is not limited to:
- Logging in
- Chat
- Multiplayer
- Spectator
- Server Bot (RealistikBot)

## Why is our fork better?
This fork of pep.py has been developed specifically to suit the need of RealistikOsu. With the rapid growth of the server, more and more demand has been placed on us in regards of features alongside performance. The original repo features a large quantity of fatal flaws alongside performance hogs, and through our usage of the software, we have solved a majority of those issues.

- Full Dockerisation
- Fixed multiplayer
- Major performance optimisations.
- Relax and Autopilot support
- Extended Redis API
- Extended 3rd party API support
- Customised HWID system
- Extended in-game bot commands
- Python 3.9 support

## Requirements
To run pep.py, there is an list of requirements to ensure the server runs at all.
- Python >=3.9
- RealistikOsu MySQL Database
