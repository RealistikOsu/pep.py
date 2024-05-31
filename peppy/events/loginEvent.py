from __future__ import annotations

import random
import sys
import time
import traceback
from datetime import datetime

from common.constants import privileges
from common.ripple import userUtils
from common.ripple.userUtils import restrict_with_log
from config import config
from constants import exceptions
from constants import serverPackets
from helpers import chatHelper as chat
from helpers import geo_helper
from helpers.geo_helper import get_full
from helpers.realistik_stuff import Timer
from helpers.user_helper import get_country
from helpers.user_helper import set_country
from helpers.user_helper import verify_password
from logger import log
from objects import glob

UNFREEZE_NOTIF = serverPackets.notification(
    "Thank you for providing a liveplay! You have proven your legitemacy and "
    f"have subsequently been unfrozen. Have fun playing {config.SRV_NAME}!",
)
FREEZE_RES_NOTIF = serverPackets.notification(
    "Your window for liveplay sumbission has expired! Your account has been "
    "restricted as per our cheating policy. Please contact staff for more "
    f"information on what can be done. This can be done via the {config.SRV_NAME} Discord server.",
)
FALLBACK_NOTIF = serverPackets.notification(
    f"Fallback clients are not supported by {config.SRV_NAME}. This is due to a combination of missing features "
    f"and server security. Please use a modern build of osu! to play {config.SRV_NAME}.",
)
OLD_CLIENT_NOTIF = serverPackets.notification(
    f"You are using an outdated client (minimum release year {config.SRV_MIN_CLIENT_YEAR}). "
    f"Please update your client to the latest version to play {config.SRV_NAME}.",
)
BOT_ACCOUNT_RESPONSE = serverPackets.notification(
    f"You may not log into a bot account using a real client. Please use a bot client to play {config.SRV_NAME}.",
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
            log.error("Login error (invalid login data)!")
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
            log.error(f"Login failed for user {username} (user not found)!")
            responseData += serverPackets.notification(
                f"{config.SRV_NAME}: This user does not exist!",
            )
            raise exceptions.loginFailedException()

        userID = user_db["id"]
        priv = int(user_db["privileges"])
        silence_end = int(user_db["silence_end"])
        donor_expire = int(user_db["donor_expire"])

        # check if its a client trying to log into a bot account
        if priv & privileges.USER_BOT and osuVersion != "bot_account":
            raise exceptions.botAccountException()

        if not verify_password(userID, loginData[1]):
            # Invalid password
            log.error(f"Login failed for user {username} (invalid password)!")
            responseData += serverPackets.notification(
                f"{config.SRV_NAME}: Invalid password!",
            )
            raise exceptions.loginFailedException()

        # Make sure we are not banned or locked
        if (not priv & 3 > 0) and (not priv & privileges.USER_PENDING_VERIFICATION):
            log.error(f"Login failed for user {username} (user is banned)!")
            raise exceptions.loginBannedException()

        # Verify this user (if pending activation)
        firstLogin = False
        if (
            priv
            & privileges.USER_PENDING_VERIFICATION
            # or not userUtils.hasVerifiedHardware(userID)
        ):
            if userUtils.verifyUser(userID, clientData):
                # Valid account
                log.info(f"Account {userID} verified successfully!")
                firstLogin = True
            else:
                # Multiaccount detected
                log.info(f"Account {userID} NOT verified!")
                raise exceptions.loginBannedException()

        # Check restricted mode (and eventually send message)
        # Cache this for less db queries
        user_restricted = (priv & privileges.USER_NORMAL) and not (
            priv & privileges.USER_PUBLIC
        )

        # Save HWID in db for multiaccount detection
        if not priv & privileges.USER_BOT:
            hwAllowed = userUtils.logHardware(
                user_id=userID,
                hashes=clientData,
                is_restricted=user_restricted,
                activation=firstLogin,
                bypass_restrict=user_db["bypass_hwid"],
            )

            # This is false only if HWID is empty
            # if HWID is banned, we get restricted so there's no
            # need to deny bancho access
            if not hwAllowed:
                raise exceptions.haxException()

        # Log user IP
        userUtils.logIP(userID, requestIP)

        # Log user osuver
        glob.db.execute(
            "UPDATE users SET osuver = %s WHERE id = %s LIMIT 1",
            [osuVersion, userID],
        )

        # Delete old tokens for that user and generate a new one
        isTournament = "tourney" in osuVersion
        if not isTournament:
            glob.tokens.deleteOldTokens(userID)
        responseToken = glob.tokens.addToken(
            userID,
            requestIP,
            timeOffset=timeOffset,
            tournament=isTournament,
        )
        responseTokenString = responseToken.token

        if user_restricted:
            responseToken.notify_restricted()
        # responseToken.checkRestricted()

        # Check if frozen
        frozen = user_db["frozen"]

        current = datetime.now()
        expire = datetime.utcfromtimestamp(user_db["freezedate"])
        readabledate = expire.strftime("%d-%m-%Y %H:%M:%S")
        passed = current > expire
        if frozen and not passed:
            responseToken.enqueue(
                serverPackets.notification(
                    f"The {config.SRV_NAME} staff team has found you suspicious and would like to request a liveplay. "
                    f"You have until {readabledate} (UTC) to provide a liveplay to the staff team. This can be done via "
                    f"the {config.SRV_NAME} Discord server. Failure to provide a valid liveplay will result in your account "
                    "being automatically restricted.",
                ),
            )
        elif frozen and passed:
            responseToken.enqueue(FREEZE_RES_NOTIF)
            restrict_with_log(
                userID,
                "Time window for liveplay expired",
                "The time window for the user to submit a liveplay has expired. The user has been automatically restricted.",
            )

        # we thank unfrozen people
        if not frozen and user_db["firstloginafterfrozen"]:
            responseToken.enqueue(UNFREEZE_NOTIF)
            glob.db.execute(
                f"UPDATE users SET firstloginafterfrozen = 0 WHERE id = {userID}",
            )

        # Send message if donor expires soon
        if responseToken.privileges & privileges.USER_DONOR:
            if donor_expire - int(time.time()) <= 86400 * 3:
                expireDays = round((donor_expire - int(time.time())) / 86400)
                expireIn = (
                    f"{expireDays} days" if expireDays > 1 else "less than 24 hours"
                )
                responseToken.enqueue(
                    serverPackets.notification(
                        f"Your supporter status expires in {expireIn}! Following this, you will lose your supporter privileges "
                        "(such as the further profile customisation options, name changes or profile wipes) and will not "
                        f"be able to access supporter features. If you wish to keep supporting {config.SRV_NAME} and you "
                        "don't want to lose your donor privileges, you can donate again by clicking on 'Donate' on our website.",
                    ),
                )

        # Get only silence remaining seconds
        responseToken.silenceEndTime = silence_end
        silenceSeconds = responseToken.getSilenceSecondsLeft()
        # Get supporter/GMT
        userGMT = False
        userTournament = False
        userGMT = responseToken.admin
        userTournament = bool(
            responseToken.privileges & privileges.USER_TOURNAMENT_STAFF,
        )

        # Server restarting check
        if glob.restarting:
            raise exceptions.banchoRestartingException()

        # Maintenance check
        if glob.banchoConf.config["banchoMaintenance"]:
            if not userGMT:
                # We are not mod/admin, delete token, send notification and logout
                glob.tokens.deleteToken(responseTokenString)
                raise exceptions.banchoMaintenanceException()
            else:
                # We are mod/admin, send warning notification and continue
                responseToken.enqueue(
                    serverPackets.notification(
                        "Bancho is in maintenance mode. Only mods/admins have full access to the server.\nType !system maintenance off in chat to turn off maintenance mode.",
                    ),
                )

        # BAN CUSTOM CHEAT CLIENTS
        # 0Ainu = First Ainu build
        # b20190326.2 = Ainu build 2 (MPGH PAGE 10)
        # b20190401.22f56c084ba339eefd9c7ca4335e246f80 = Ainu Aoba's Birthday Build
        # b20191223.3 = Unknown Ainu build? (Taken from most users osuver in cookiezi.pw)
        # b20190226.2 = hqOsu (hq-af)

        # TODO: Rewrite this mess
        # Ainu Client 2020 update
        if not priv & privileges.USER_BOT:
            if tornadoRequest.request.headers.get("ainu"):
                log.info(f"Account {userID} tried to use Ainu Client 2020!")
                if user_restricted:
                    responseToken.enqueue(serverPackets.notification("Nice try BUDDY."))
                else:
                    glob.tokens.deleteToken(userID)
                    restrict_with_log(
                        userID,
                        "Attempted login with Ainu Client 2020",
                        "The user has attempted to log in with a the Ainu 2020 client. "
                        "This is a known cheating client. The user has been detected through "
                        "the ainu header sent on login. (login gate).",
                    )
                    raise exceptions.loginCheatClientsException()
            # Ainu Client 2019
            elif osuVersion in (
                "0Ainu",
                "b20190326.2",
                "b20190401.22f56c084ba339eefd9c7ca4335e246f80",
                "b20191223.3",
            ):
                log.info(f"Account {userID} tried to use Ainu Client!")
                if user_restricted:
                    responseToken.enqueue(serverPackets.notification("Nice try BUDDY."))
                else:
                    glob.tokens.deleteToken(userID)
                    restrict_with_log(
                        userID,
                        "Attempted login with Ainu Client",
                        "The user has attempted to log in with a client which has a version "
                        f"matching known Ainu cheating client versions ({osuVersion}). "
                        "(login gate)",
                    )
                    raise exceptions.loginCheatClientsException()
            # hqOsu
            elif osuVersion == "b20190226.2":
                log.info(f"Account {userID} tried to use hqOsu!")
                if user_restricted:
                    responseToken.enqueue(serverPackets.notification("Comedian."))
                else:
                    glob.tokens.deleteToken(userID)
                    restrict_with_log(
                        userID,
                        "Attempted login with hqOsu",
                        "The user has attempted to log in with a client version matching "
                        f"the default setting of the hQosu multiaccounting utility ({osuVersion}). "
                        "(login gate)",
                    )
                    raise exceptions.loginCheatClientsException()

            # hqosu legacy
            elif osuVersion == "b20190716.5":
                log.info(f"Account {userID} tried to use hqOsu legacy!")
                if user_restricted:
                    responseToken.enqueue(serverPackets.notification("Comedian."))
                else:
                    glob.tokens.deleteToken(userID)
                    restrict_with_log(
                        userID,
                        "Attempted login with hqOsu (legacy)",
                        "The user has attempted to log in with a client version matching "
                        f"the default setting of the hQosu multiaccounting utility ({osuVersion}). "
                        "(login gate)",
                    )
                    raise exceptions.loginCheatClientsException()
            # Budget Hacked client.
            elif osuVersion.startswith("skoot"):
                if user_restricted:
                    responseToken.enqueue(serverPackets.notification("Comedian."))
                else:
                    glob.tokens.deleteToken(userID)
                    restrict_with_log(
                        userID,
                        "Attempted login with Skoot client.",
                        "The user attempted to log in with the Skoot custom client. "
                        f"This has been detected through the osu! version sent on login ({osuVersion}). "
                        "(login gate)",
                    )
                    raise exceptions.loginCheatClientsException()

            # Blanket cover for most retard clients, force update.
            elif osuVersion[0] != "b":
                glob.tokens.deleteToken(userID)
                raise exceptions.haxException()

            # Special case for old fallback client
            elif osuVersion == "20160403.6":
                glob.tokens.deleteToken(userID)
                responseData += FALLBACK_NOTIF
                raise exceptions.loginFailedException

            # Misc outdated client check
            elif int(osuVersion[1:5]) < config.SRV_MIN_CLIENT_YEAR:
                glob.tokens.deleteToken(userID)
                responseData += OLD_CLIENT_NOTIF
                raise exceptions.loginFailedException

        # Send all needed login packets
        responseToken.enqueue(
            bytearray(serverPackets.silence_end_notify(silenceSeconds))
            + serverPackets.login_reply(userID)  # Fast addition
            + serverPackets.protocol_version()
            + serverPackets.bancho_priv(True, userGMT, userTournament)
            + serverPackets.user_presence(userID, True)
            + serverPackets.user_stats(userID)
            + serverPackets.channel_info_end()
            + serverPackets.friend_list(userID),
        )

        # Default opened channels
        # TODO: Configurable default channels
        chat.joinChannel(token=responseToken, channel="#osu")
        chat.joinChannel(token=responseToken, channel="#announce")

        # Join admin channel if we are an admin
        if responseToken.admin:
            chat.joinChannel(token=responseToken, channel="#admin")

        # Output channels info
        for key, value in glob.channels.channels.items():
            if value.publicRead and not value.hidden:
                responseToken.enqueue(serverPackets.channel_info(key))

        # Send main menu icon
        if glob.banchoConf.config["menuIcon"] != "":
            responseToken.enqueue(
                serverPackets.menu_icon(glob.banchoConf.config["menuIcon"]),
            )

        # Send online users' panels
        with glob.tokens:
            for token in glob.tokens.tokens.values():
                if not token.restricted:
                    responseToken.enqueue(serverPackets.user_presence(token.userID))

        # Localise the user based off IP.
        # Get location and country from IP
        latitude, longitude, countryLetters = get_full(requestIP)

        country = geo_helper.getCountryID(countryLetters)

        # Set location and country
        responseToken.setLocation(latitude, longitude)
        responseToken.country = country

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
                f"Hello I'm {config.SRV_BOT_NAME}! The server's official bot to assist you, "
                "if you want to know what I can do just type !help"
            )
        else:
            quote = random.choice(glob.banchoConf.config["Quotes"])
        notif = f"""- Online Users: {online_users}\n- {quote}"""
        if responseToken.admin:
            notif += f"\n- Elapsed: {t_str}!"
        responseToken.enqueue(serverPackets.notification(notif))

        log.info(f"Authentication attempt took {t_str}!")

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
        log.error(
            "Unknown error!\n```\n{}\n{}```".format(
                sys.exc_info(),
                traceback.format_exc(),
            ),
        )
        responseData += serverPackets.login_reply(-5)  # Bancho error
        responseData += serverPackets.notification(
            f"{config.SRV_NAME}: The server has experienced an error while logging you "
            "in! Please notify the developers for help.",
        )
    finally:
        # Return token string and data
        return responseTokenString, bytes(responseData)
