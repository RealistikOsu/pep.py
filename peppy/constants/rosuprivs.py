# Rosu specific privilege constants
# If you fork please change these.
# Message to self: If you mess with these in the db, you suffer for hardcoding these.
# Hardcoding is the perfect, most maintainable way.
from __future__ import annotations

OWNER = 942669823
DEVELOPER = 672131067
DEV_SUPPORTER = 992799  # This is lenforiees fault.
ADMIN = 940572671
BAT = 267
COMMUNITY_MANAGER = 806224383
MODERATOR = 786683
DONOR = 7

ADMIN_PRIVS = (DEVELOPER, OWNER, ADMIN, DEV_SUPPORTER)
