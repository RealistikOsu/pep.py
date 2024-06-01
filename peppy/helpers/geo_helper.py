from __future__ import annotations

import settings
from geoip2 import database

db_reader = database.Reader(settings.DATA_GEOLOCATION_PATH)

countryCodes = {
    "IO": 104,
    "PS": 178,
    "LV": 132,
    "GI": 82,
    "MZ": 154,
    "BZ": 37,
    "TR": 217,
    "CV": 52,
    "BI": 26,
    "CM": 47,
    "JM": 109,
    "GU": 91,
    "CY": 54,
    "BW": 35,
    "KW": 120,
    "MY": 153,
    "SH": 193,
    "PG": 171,
    "PW": 180,
    "FM": 72,
    "HR": 97,
    "YT": 238,
    "JO": 110,
    "HK": 94,
    "MW": 151,
    "AZ": 18,
    "IQ": 105,
    "DO": 60,
    "RS": 239,
    "PK": 173,
    "BR": 31,
    "SN": 199,
    "LI": 126,
    "CD": 40,
    "MG": 137,
    "PE": 169,
    "CK": 45,
    "SJ": 195,
    "SZ": 205,
    "PM": 175,
    "LY": 133,
    "BV": 34,
    "KN": 117,
    "GR": 88,
    "CC": 39,
    "IN": 103,
    "DZ": 61,
    "SK": 196,
    "VC": 229,
    "GW": 92,
    "BQ": 0,
    "UM": 224,
    "AF": 5,
    "TZ": 221,
    "AO": 11,
    "AW": 17,
    "AE": 0,
    "PF": 170,
    "MK": 139,
    "AR": 13,
    "AQ": 12,
    "SL": 197,
    "HT": 98,
    "NF": 158,
    "SS": 190,
    "MU": 149,
    "VA": 228,
    "EC": 62,
    "LC": 125,
    "MX": 152,
    "CW": 0,
    "LT": 130,
    "GN": 85,
    "ZM": 241,
    "LU": 131,
    "NG": 159,
    "MS": 147,
    "MV": 150,
    "DJ": 57,
    "MQ": 145,
    "IE": 101,
    "CG": 40,
    "LK": 127,
    "NZ": 166,
    "KR": 119,
    "RO": 184,
    "KE": 112,
    "MF": 252,
    "SR": 201,
    "PA": 168,
    "KI": 115,
    "NL": 161,
    "DM": 59,
    "TC": 206,
    "KZ": 122,
    "CR": 50,
    "NR": 164,
    "UZ": 227,
    "GE": 79,
    "KP": 118,
    "PN": 176,
    "BY": 36,
    "NI": 160,
    "IR": 106,
    "VI": 232,
    "MA": 134,
    "NO": 162,
    "PT": 179,
    "PY": 181,
    "CU": 51,
    "SC": 189,
    "TT": 218,
    "CA": 38,
    "IT": 108,
    "GF": 80,
    "CN": 48,
    "GQ": 87,
    "LR": 128,
    "BA": 19,
    "TD": 207,
    "AU": 16,
    "MM": 141,
    "HU": 99,
    "EG": 64,
    "JE": 250,
    "IL": 102,
    "BL": 251,
    "BS": 32,
    "SE": 191,
    "MC": 135,
    "SD": 190,
    "ZA": 240,
    "IM": 249,
    "MO": 143,
    "GL": 83,
    "TV": 219,
    "FK": 71,
    "GB": 77,
    "NA": 155,
    "AM": 9,
    "WS": 236,
    "UY": 226,
    "EE": 63,
    "TL": 216,
    "BT": 33,
    "VU": 234,
    "WF": 235,
    "AX": 247,
    "TK": 212,
    "MN": 142,
    "SB": 188,
    "XK": 0,
    "BH": 25,
    "ID": 100,
    "SV": 203,
    "TG": 209,
    "BF": 23,
    "GG": 248,
    "IS": 107,
    "FJ": 70,
    "KG": 113,
    "BD": 21,
    "ZW": 243,
    "AI": 7,
    "NP": 163,
    "KH": 114,
    "BJ": 27,
    "EH": 65,
    "BE": 22,
    "SM": 198,
    "CX": 53,
    "TW": 220,
    "KM": 116,
    "AS": 14,
    "AT": 15,
    "LA": 123,
    "US": 225,
    "SY": 204,
    "SO": 200,
    "AD": 3,
    "OM": 167,
    "GT": 90,
    "CF": 41,
    "GY": 93,
    "VN": 233,
    "VE": 230,
    "PH": 172,
    "TM": 213,
    "VG": 231,
    "GP": 86,
    "CZ": 55,
    "GM": 84,
    "MR": 146,
    "TN": 214,
    "SI": 194,
    "TO": 215,
    "UG": 223,
    "SA": 187,
    "ST": 202,
    "QA": 182,
    "FI": 69,
    "CO": 49,
    "AG": 6,
    "PR": 177,
    "PL": 174,
    "GH": 81,
    "GA": 76,
    "TJ": 211,
    "SX": 0,
    "KY": 121,
    "BO": 30,
    "UA": 222,
    "MP": 144,
    "TF": 208,
    "LB": 124,
    "MT": 148,
    "FR": 74,
    "JP": 111,
    "RU": 185,
    "RW": 186,
    "NC": 156,
    "NE": 157,
    "BN": 29,
    "CI": 44,
    "TH": 210,
    "DE": 56,
    "ET": 68,
    "FO": 73,
    "YE": 237,
    "DK": 58,
    "BG": 24,
    "GS": 89,
    "HM": 95,
    "BB": 20,
    "BM": 28,
    "ML": 140,
    "SG": 192,
    "GD": 78,
    "NU": 165,
    "RE": 183,
    "LS": 129,
    "ER": 66,
    "ME": 242,
    "HN": 96,
    "AL": 8,
    "CH": 43,
    "MD": 136,
    "ES": 67,
    "CL": 46,
    "MH": 138,
}


def getCountryID(code):
    """
    Get osu country ID from country letters

    :param code: country letters (eg: US)
    :return: country osu code
    """

    ccode = countryCodes.get(code)
    return ccode if ccode is not None else 0


def getCountryLetters(code):
    """
    Get country letters from osu country ID

    :param code: osu country ID
    :return: country letters (XX if not found)
    """
    for key, value in countryCodes.items():
        if value == code:
            return key

    return "XX"


def get_full(ip: str) -> tuple[float, float, str]:
    """Fetches the user's full geolocation data and returns the imperative
    info retrieved.

    Note:
            This uses a really quick IP lookup database. use as a replacement to
        full on API requests.

    Args:
            ip (str): The IP of the user to fetch the info for.

    Returns:
            Tuple of data in order of `(lat, long, country)`
    """

    try:
        city = db_reader.city(ip)

        return city.location.latitude, city.location.longitude, city.country.iso_code  # type: ignore L

    except Exception:
        return 0.0, 0.0, "XX"
