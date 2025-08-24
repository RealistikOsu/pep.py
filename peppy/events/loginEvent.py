from __future__ import annotations

import logging
import random
import sys
import time
import traceback
from datetime import datetime

import settings
from common.constants import privileges
from common.ripple import userUtils
from common.ripple.userUtils import restrict_with_log
from constants import exceptions
from constants import serverPackets
from helpers import chatHelper as chat
from helpers import geo_helper
from helpers.timing import Timer
from helpers.user_helper import get_country
from helpers.user_helper import set_country
from helpers.user_helper import verify_password
from objects import glob

logger = logging.getLogger(__name__)

UNFREEZE_NOTIF = serverPackets.notification(
    "Thank you for providing a liveplay! You have proven your legitemacy and "
    f"have subsequently been unfrozen. Have fun playing {settings.PS_NAME}!",
)
FREEZE_RES_NOTIF = serverPackets.notification(
    "Your window for liveplay sumbission has expired! Your account has been "
    "restricted as per our cheating policy. Please contact staff for more "
    f"information on what can be done. This can be done via the {settings.PS_NAME} Discord server.",
)
FALLBACK_NOTIF = serverPackets.notification(
    f"Fallback clients are not supported by {settings.PS_NAME}. This is due to a combination of missing features "
    f"and server security. Please use a modern build of osu! to play {settings.PS_NAME}.",
)
OLD_CLIENT_NOTIF = serverPackets.notification(
    f"You are using an outdated client (minimum release year {settings.PS_MINIMUM_CLIENT_YEAR}). "
    f"Please update your client to the latest version to play {settings.PS_NAME}.",
)
BOT_ACCOUNT_RESPONSE = serverPackets.notification(
    f"You may not log into a bot account using a real client. Please use a bot client to play {settings.PS_NAME}.",
)


def handle(tornadoRequest):
    # I wanna benchmark!
    t = Timer()
    t.start()
    # Data to return
    responseToken = None
    responseTokenString = ""
    responseData = bytearray()

    # Get IP from tornado request
    requestIP = tornadoRequest.getRequestIP()

    # Split POST body so we can get username/password/hardware data
    # 2:-3 thing is because requestData has some escape stuff that we don't need
    loginData = str(tornadoRequest.request.body)[2:-3].split("\\n")
    try:
        # Make sure loginData is valid
        if len(loginData) < 3:
            logger.error("Login error (invalid login data)!")
            raise exceptions.invalidArgumentsException()

        # Get HWID, MAC address and more
        # Structure (new line = "|", already split)
        # [0] osu! version
        # [1] plain mac addressed, separated by "."
        # [2] mac addresses hash set
        # [3] unique ID
        # [4] disk ID
        splitData = loginData[2].split("|")
        osuVersion = splitData[0]
        timeOffset = int(splitData[1])
        clientData = splitData[3].split(":")[:5]
        if len(clientData) < 4:
            raise exceptions.forceUpdateException()

        # Try to get the ID from username
        username = str(loginData[0])
        safe_username = username.rstrip().replace(" ", "_").lower()

        # Set stuff from single query rather than many userUtils calls.
        user_db = glob.db.fetch(
            "SELECT id, privileges, silence_end, donor_expire, frozen, "
            "firstloginafterfrozen, freezedate, bypass_hwid, country FROM users "
            "WHERE username_safe = %s LIMIT 1",
            (safe_username,),
        )

        if not user_db:
            # Invalid username
            logger.error("Login failed - user not found", extra={"username": username})
            responseData += serverPackets.notification(
                f"{settings.PS_NAME}: This user does not exist!",
            )
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Get user ID and privileges
        userID = user_db["id"]
        userPrivileges = user_db["privileges"]

        # Check if user is frozen
        if user_db["frozen"]:
            # Check if this is their first login after being frozen
            if user_db["firstloginafterfrozen"]:
                # Unfreeze them
                glob.db.execute(
                    "UPDATE users SET frozen = 0, firstloginafterfrozen = 0 WHERE id = %s",
                    (userID,),
                )
                responseData += UNFREEZE_NOTIF
            else:
                # Still frozen
                responseData += serverPackets.notification(
                    "Your account is frozen. Please contact staff for more information.",
                )
                responseData += serverPackets.login_failed()
                return responseTokenString, bytes(responseData)

        # Check if user is banned
        if userPrivileges & privileges.USER_PUBLIC == 0:
            responseData += serverPackets.login_banned()
            return responseTokenString, bytes(responseData)

        # Check if user is silenced
        if user_db["silence_end"] > time.time():
            responseData += serverPackets.notification(
                f"You are silenced until {datetime.fromtimestamp(user_db['silence_end']).strftime('%Y-%m-%d %H:%M:%S')} UTC.",
            )

        # Check if user is donor
        if user_db["donor_expire"] > time.time():
            userPrivileges |= privileges.USER_DONOR

        # Verify password
        if not verify_password(str(loginData[1]), userID):
            logger.error(
                "Login failed - invalid password", extra={"username": username},
            )
            responseData += serverPackets.notification(
                f"{settings.PS_NAME}: Invalid password!",
            )
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is restricted
        if userPrivileges & privileges.USER_PUBLIC == 0:
            responseData += serverPackets.login_banned()
            return responseTokenString, bytes(responseData)

        # Check if user is using a bot account
        if userID == settings.PS_BOT_USER_ID:
            responseData += BOT_ACCOUNT_RESPONSE
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is using an old client
        if int(osuVersion.split(".")[0]) < settings.PS_MINIMUM_CLIENT_YEAR:
            responseData += OLD_CLIENT_NOTIF
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is using a fallback client
        if "fallback" in osuVersion.lower():
            responseData += FALLBACK_NOTIF
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is using a cheat client
        if any(
            cheat in osuVersion.lower() for cheat in ["hack", "cheat", "mod", "multi"]
        ):
            responseData += serverPackets.login_cheats()
            return responseTokenString, bytes(responseData)

        # Check if user is using a VPN
        is_vpn = geo_helper.is_vpn(requestIP)
        if is_vpn and not user_db["bypass_hwid"]:
            responseData += serverPackets.notification(
                "VPN usage is not allowed on this server.",
            )
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Get country from IP
        countryLetters = get_country(requestIP)
        latitude, longitude = geo_helper.get_coordinates(requestIP)

        # Create token
        responseToken = glob.tokens.addToken(userID)
        responseTokenString = responseToken.token

        # Set token properties
        responseToken.username = username
        responseToken.privileges = userPrivileges
        responseToken.restricted = userPrivileges & privileges.USER_PUBLIC == 0
        responseToken.admin = userPrivileges & privileges.ADMIN_MANAGE_USERS > 0
        responseToken.setLocation(latitude, longitude)
        responseToken.country = countryLetters

        # Log for country tagging feature
        if countryLetters != "XX":
            glob.db.execute(
                "INSERT INTO user_country_history (user_id, country_code, is_vpn, ip_address) "
                "VALUES (%s, %s, %s, %s)",
                (userID, countryLetters, is_vpn, requestIP),
            )

        # Set country in db if user has no country (first bancho login)
        if user_db["country"] == "XX":
            set_country(userID, countryLetters)

        # Send to everyone our userpanel if we are not restricted or tournament
        if not responseToken.restricted:
            glob.streams.broadcast("main", serverPackets.user_presence(userID))

        # TODO: Make quotes database based.
        t_str = t.end_time_str()
        online_users = len(glob.tokens.tokens)

        # Wylie has his own quote he gets to enjoy only himself lmfao. UPDATE: Electro gets it too.
        if userID in (4674, 3277):
            quote = "I lost an S because I saw her lewd"
        # Ced also gets his own AS HE DOESNT WANT TO CHECK FAST SPEED.
        elif userID == 1002:
            quote = "juSt Do iT"
        # Me and relesto are getting one as well lmao. UPDATE: Sky and Aochi gets it too lmao.
        elif userID in (1000, 1180, 3452, 4812):
            quote = (
                f"Hello I'm {settings.PS_BOT_USERNAME}! The server's official bot to assist you, "
                "if you want to know what I can do just type !help"
            )
        else:
            quote = random.choice(glob.banchoConf.config["Quotes"])
        notif = f"""- Online Users: {online_users}\n- {quote}"""
        if responseToken.admin:
            notif += f"\n- Elapsed: {t_str}!"
        responseToken.enqueue(serverPackets.notification(notif))

        logger.info("Authentication attempt completed", extra={"duration": t_str})

        # Set reponse data to right value and reset our queue
        responseData = responseToken.fetch_queue()
    except exceptions.loginFailedException:
        # Login failed error packet
        # (we don't use enqueue because we don't have a token since login has failed)
        responseData += serverPackets.login_failed()
    except exceptions.invalidArgumentsException:
        # Invalid POST data
        # (we don't use enqueue because we don't have a token since login has failed)
        responseData += serverPackets.login_failed()
    except exceptions.loginBannedException:
        # Login banned error packet
        responseData += serverPackets.login_banned()
    except exceptions.loginCheatClientsException:
        # Banned for logging in with cheats
        responseData += serverPackets.login_cheats()
    except exceptions.banchoMaintenanceException:
        # Bancho is in maintenance mode
        responseData = b""
        if responseToken is not None:
            responseData = responseToken.fetch_queue()
        responseData += serverPackets.notification(
            "Our bancho server is in maintenance mode. Please try to login again later.",
        )
        responseData += serverPackets.login_failed()
    except exceptions.banchoRestartingException:
        # Bancho is restarting
        responseData += serverPackets.notification(
            "Bancho is restarting. Try again in a few minutes.",
        )
        responseData += serverPackets.login_failed()
    except exceptions.need2FAException:
        # User tried to log in from unknown IP
        responseData += serverPackets.verification_required()
    except exceptions.haxException:
        # Using oldoldold client, we don't have client data. Force update.
        # (we don't use enqueue because we don't have a token since login has failed)
        responseData += serverPackets.force_update()
    except exceptions.botAccountException:
        return "no", BOT_ACCOUNT_RESPONSE + serverPackets.login_failed()
    except Exception:
        logger.error(
            "Unknown error!\n```\n{}\n{}```".format(
                sys.exc_info(),
                traceback.format_exc(),
            ),
        )
        responseData += serverPackets.login_reply(-5)  # Bancho error
        responseData += serverPackets.notification(
            f"{settings.PS_NAME}: The server has experienced an error while logging you "
            "in! Please notify the developers for help.",
        )
    finally:
        # Return token string and data
        return responseTokenString, bytes(responseData)


async def handle_fastapi(request):
    """FastAPI-compatible version of the handle function."""
    # I wanna benchmark!
    t = Timer()
    t.start()
    # Data to return
    responseToken = None
    responseTokenString = ""
    responseData = bytearray()

    # Get IP from FastAPI request
    requestIP = get_request_ip_fastapi(request)

    # Split POST body so we can get username/password/hardware data
    # 2:-3 thing is because requestData has some escape stuff that we don't need
    request_body = await request.body()
    loginData = str(request_body)[2:-3].split("\\n")
    try:
        # Make sure loginData is valid
        if len(loginData) < 3:
            logger.error("Login error (invalid login data)!")
            raise exceptions.invalidArgumentsException()

        # Get HWID, MAC address and more
        # Structure (new line = "|", already split)
        # [0] osu! version
        # [1] plain mac addressed, separated by "."
        # [2] mac addresses hash set
        # [3] unique ID
        # [4] disk ID
        splitData = loginData[2].split("|")
        osuVersion = splitData[0]
        timeOffset = int(splitData[1])
        clientData = splitData[3].split(":")[:5]
        if len(clientData) < 4:
            raise exceptions.forceUpdateException()

        # Try to get the ID from username
        username = str(loginData[0])
        safe_username = username.rstrip().replace(" ", "_").lower()

        # Set stuff from single query rather than many userUtils calls.
        user_db = glob.db.fetch(
            "SELECT id, privileges, silence_end, donor_expire, frozen, "
            "firstloginafterfrozen, freezedate, bypass_hwid, country FROM users "
            "WHERE username_safe = %s LIMIT 1",
            (safe_username,),
        )

        if not user_db:
            # Invalid username
            logger.error("Login failed - user not found", extra={"username": username})
            responseData += serverPackets.notification(
                f"{settings.PS_NAME}: This user does not exist!",
            )
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Get user ID and privileges
        userID = user_db["id"]
        userPrivileges = user_db["privileges"]

        # Check if user is frozen
        if user_db["frozen"]:
            # Check if this is their first login after being frozen
            if user_db["firstloginafterfrozen"]:
                # Unfreeze them
                glob.db.execute(
                    "UPDATE users SET frozen = 0, firstloginafterfrozen = 0 WHERE id = %s",
                    (userID,),
                )
                responseData += UNFREEZE_NOTIF
            else:
                # Still frozen
                responseData += serverPackets.notification(
                    "Your account is frozen. Please contact staff for more information.",
                )
                responseData += serverPackets.login_failed()
                return responseTokenString, bytes(responseData)

        # Check if user is banned
        if userPrivileges & privileges.USER_PUBLIC == 0:
            responseData += serverPackets.login_banned()
            return responseTokenString, bytes(responseData)

        # Check if user is silenced
        if user_db["silence_end"] > time.time():
            responseData += serverPackets.notification(
                f"You are silenced until {datetime.fromtimestamp(user_db['silence_end']).strftime('%Y-%m-%d %H:%M:%S')} UTC.",
            )

        # Check if user is donor
        if user_db["donor_expire"] > time.time():
            userPrivileges |= privileges.USER_DONOR

        # Verify password
        if not verify_password(str(loginData[1]), userID):
            logger.error(
                "Login failed - invalid password", extra={"username": username},
            )
            responseData += serverPackets.notification(
                f"{settings.PS_NAME}: Invalid password!",
            )
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is restricted
        if userPrivileges & privileges.USER_PUBLIC == 0:
            responseData += serverPackets.login_banned()
            return responseTokenString, bytes(responseData)

        # Check if user is using a bot account
        if userID == settings.PS_BOT_USER_ID:
            responseData += BOT_ACCOUNT_RESPONSE
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is using an old client
        if int(osuVersion.split(".")[0]) < settings.PS_MINIMUM_CLIENT_YEAR:
            responseData += OLD_CLIENT_NOTIF
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is using a fallback client
        if "fallback" in osuVersion.lower():
            responseData += FALLBACK_NOTIF
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Check if user is using a cheat client
        if any(
            cheat in osuVersion.lower() for cheat in ["hack", "cheat", "mod", "multi"]
        ):
            responseData += serverPackets.login_cheats()
            return responseTokenString, bytes(responseData)

        # Check if user is using a VPN
        is_vpn = geo_helper.is_vpn(requestIP)
        if is_vpn and not user_db["bypass_hwid"]:
            responseData += serverPackets.notification(
                "VPN usage is not allowed on this server.",
            )
            responseData += serverPackets.login_failed()
            return responseTokenString, bytes(responseData)

        # Get country from IP
        countryLetters = get_country(requestIP)
        latitude, longitude = geo_helper.get_coordinates(requestIP)

        # Create token
        responseToken = glob.tokens.addToken(userID)
        responseTokenString = responseToken.token

        # Set token properties
        responseToken.username = username
        responseToken.privileges = userPrivileges
        responseToken.restricted = userPrivileges & privileges.USER_PUBLIC == 0
        responseToken.admin = userPrivileges & privileges.ADMIN_MANAGE_USERS > 0
        responseToken.setLocation(latitude, longitude)
        responseToken.country = countryLetters

        # Log for country tagging feature
        if countryLetters != "XX":
            glob.db.execute(
                "INSERT INTO user_country_history (user_id, country_code, is_vpn, ip_address) "
                "VALUES (%s, %s, %s, %s)",
                (userID, countryLetters, is_vpn, requestIP),
            )

        # Set country in db if user has no country (first bancho login)
        if user_db["country"] == "XX":
            set_country(userID, countryLetters)

        # Send to everyone our userpanel if we are not restricted or tournament
        if not responseToken.restricted:
            glob.streams.broadcast("main", serverPackets.user_presence(userID))

        # TODO: Make quotes database based.
        t_str = t.end_time_str()
        online_users = len(glob.tokens.tokens)

        # Wylie has his own quote he gets to enjoy only himself lmfao. UPDATE: Electro gets it too.
        if userID in (4674, 3277):
            quote = "I lost an S because I saw her lewd"
        # Ced also gets his own AS HE DOESNT WANT TO CHECK FAST SPEED.
        elif userID == 1002:
            quote = "juSt Do iT"
        # Me and relesto are getting one as well lmao. UPDATE: Sky and Aochi gets it too lmao.
        elif userID in (1000, 1180, 3452, 4812):
            quote = (
                f"Hello I'm {settings.PS_BOT_USERNAME}! The server's official bot to assist you, "
                "if you want to know what I can do just type !help"
            )
        else:
            quote = random.choice(glob.banchoConf.config["Quotes"])
        notif = f"""- Online Users: {online_users}\n- {quote}"""
        if responseToken.admin:
            notif += f"\n- Elapsed: {t_str}!"
        responseToken.enqueue(serverPackets.notification(notif))

        logger.info("Authentication attempt completed", extra={"duration": t_str})

        # Set reponse data to right value and reset our queue
        responseData = responseToken.fetch_queue()
    except exceptions.loginFailedException:
        # Login failed error packet
        # (we don't use enqueue because we don't have a token since login has failed)
        responseData += serverPackets.login_failed()
    except exceptions.invalidArgumentsException:
        # Invalid POST data
        # (we don't use enqueue because we don't have a token since login has failed)
        responseData += serverPackets.login_failed()
    except exceptions.loginBannedException:
        # Login banned error packet
        responseData += serverPackets.login_banned()
    except exceptions.loginCheatClientsException:
        # Banned for logging in with cheats
        responseData += serverPackets.login_cheats()
    except exceptions.banchoMaintenanceException:
        # Bancho is in maintenance mode
        responseData = b""
        if responseToken is not None:
            responseData = responseToken.fetch_queue()
        responseData += serverPackets.notification(
            "Our bancho server is in maintenance mode. Please try to login again later.",
        )
        responseData += serverPackets.login_failed()
    except exceptions.banchoRestartingException:
        # Bancho is restarting
        responseData += serverPackets.notification(
            "Bancho is restarting. Try again in a few minutes.",
        )
        responseData += serverPackets.login_failed()
    except exceptions.need2FAException:
        # User tried to log in from unknown IP
        responseData += serverPackets.verification_required()
    except exceptions.haxException:
        # Using oldoldold client, we don't have client data. Force update.
        # (we don't use enqueue because we don't have a token since login has failed)
        responseData += serverPackets.force_update()
    except exceptions.botAccountException:
        return "no", BOT_ACCOUNT_RESPONSE + serverPackets.login_failed()
    except Exception:
        logger.error(
            "Unknown error!\n```\n{}\n{}```".format(
                sys.exc_info(),
                traceback.format_exc(),
            ),
        )
        responseData += serverPackets.login_reply(-5)  # Bancho error
        responseData += serverPackets.notification(
            f"{settings.PS_NAME}: The server has experienced an error while logging you "
            "in! Please notify the developers for help.",
        )
    finally:
        # Return token string and data
        return responseTokenString, bytes(responseData)


def get_request_ip_fastapi(request):
    """
    If the server is configured to use Cloudflare, returns the `CF-Connecting-IP` header.
    Otherwise, returns the `X-Real-IP` header.

    :return: Client IP address
    """
    # Check if they are connecting through a switcher
    if (
        "ppy.sh" in request.headers.get("Host", "")
        or not settings.HTTP_USING_CLOUDFLARE
    ):
        return request.headers.get("X-Real-IP")

    return request.headers.get("CF-Connecting-IP")
