from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Optional

import requests


@dataclass
class PerformanceResult:
    stars: float
    pp: float
    ar: float
    od: float
    max_combo: int


@dataclass
class PerformanceRequest:
    beatmap_id: int
    mode: int
    mods: int
    max_combo: int
    accuracy: float
    miss_count: int
    passed_objects: Optional[int]


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
        calculation_requests: list[PerformanceRequest],
    ) -> list[dict[str, Any]]:
        respone = requests.post(
            self._base_url + "/api/v1/calculate",
            json=[
                {
                    "beatmap_id": req.beatmap_id,
                    "mode": req.mode,
                    "mods": req.mods,
                    "max_combo": req.max_combo,
                    "accuracy": req.accuracy,
                    "miss_count": req.miss_count,
                    "passed_objects": req.passed_objects,
                }
                for req in calculation_requests
            ],
            timeout=self._timeout,
        )
        respone.raise_for_status()
        return respone.json()

    def calculate_performance_single(
        self,
        beatmap_id: int,
        mode: int,
        mods: int,
        max_combo: int,
        accuracy: float,
        miss_count: int,
        passed_objects: Optional[int] = None,
    ) -> PerformanceResult:
        request = PerformanceRequest(
            beatmap_id=beatmap_id,
            mode=mode,
            mods=mods,
            max_combo=max_combo,
            accuracy=accuracy,
            miss_count=miss_count,
            passed_objects=passed_objects,
        )
        response = self.__make_performance_request([request])[0]
        return PerformanceResult(
            stars=response["stars"],
            pp=response["pp"],
            ar=response["ar"],
            od=response["od"],
            max_combo=response["max_combo"],
        )
