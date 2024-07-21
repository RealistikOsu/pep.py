from __future__ import annotations

import requests

from dataclasses import dataclass
from typing import Any
from typing import Optional

@dataclass
class PerformanceResult:
    stars: float
    pp: float
    ar: float
    od: float
    max_combo: int


class PerformanceServiceApi:
    def __init__(
            self,
            base_url: str,
            *,
            timeout: int = 1,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout

    
    def __make_performance_request(
            self,
            beatmap_id: int,
            mode: int,
            mods: int,
            max_combo: int,
            accuracy: float,
            miss_count: int,
            passed_objects: Optional[int] = None,
    ) -> dict[str, Any]:
        respone = requests.post(
            self._base_url + "/api/v1/calulcate",
            data={
                "beatmap_id": beatmap_id,
                "mode": mode,
                "mods": mods,
                "max_combo": max_combo,
                "accuracy": accuracy,
                "miss_count": miss_count,
                "passed_objects": passed_objects,
            },
            timeout=self._timeout,
        )
        respone.raise_for_status()
        return respone.json()
    

    def calculate_performance(
            self,
            beatmap_id: int,
            mode: int,
            mods: int,
            max_combo: int,
            accuracy: float,
            miss_count: int,
            passed_objects: Optional[int] = None,
    ) -> PerformanceResult:
        response = self.__make_performance_request(
            beatmap_id,
            mode,
            mods,
            max_combo,
            accuracy,
            miss_count,
            passed_objects,
        )
        return PerformanceResult(
            stars=response["stars"],
            pp=response["pp"],
            ar=response["ar"],
            od=response["od"],
            max_combo=response["max_combo"],
        )
