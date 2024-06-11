from __future__ import annotations

from dataclasses import dataclass

import requests


# Would much prefer Pydantic.
@dataclass
class IPQueryResult:
    ip: str
    country_code: str
    country_name: str
    region_name: str
    latitude: float
    longitude: float
    is_proxy: bool


IP2LOCATION_BASE_API = "https://api.ip2location.io/"
"""The default root endpoint for the IP2Location API."""


class GeolocationException(Exception):
    ...


class Ip2LocationApi:
    def __init__(
        self,
        api_key: str,
        *,
        api_root_url: str = IP2LOCATION_BASE_API,
        silent_fail: bool = False,
    ) -> None:
        self.root_url = api_root_url
        self.api_key = api_key
        self.silent_fail = silent_fail

    def query_ip(self, ip_address: str) -> IPQueryResult | None:
        query_response = requests.get(
            self.root_url,
            params={
                "key": self.api_key,
                "ip": ip_address,
            },
        ).json()

        if "error" in query_response:
            if self.silent_fail:
                return None

            error_text = query_response["error"]["error_message"]
            error_code = query_response["error"]["error_code"]
            raise GeolocationException(
                f"Failed to geolocate with error {error_text!r} ({error_code})",
            )

        return IPQueryResult(
            ip=query_response["ip"],
            country_code=query_response["country_code"],
            country_name=query_response["country_name"],
            region_name=query_response["region_name"],
            latitude=query_response["latitude"],
            longitude=query_response["longitude"],
            is_proxy=query_response["is_proxy"],
        )
