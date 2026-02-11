from typing import List

from ground.models import Telemetry
from ground.api.schemas import LastStatus, TelemetryPoint
from ground.api.telemetry_repository import TelemetryRepository


class TelemetryService:
    def __init__(self, repository: TelemetryRepository):
        self.repository = repository

    async def save_telemetry(self, telemetry: Telemetry) -> None:
        await self.repository.save_telemetry(telemetry.satellite_id, telemetry.metric_id, telemetry.value)

    async def get_realtime_status(self, satellite_id: int) -> LastStatus:
        response = await self.repository.get_realtime_status(satellite_id)
        return LastStatus(**response)

    async def get_history(self, satellite_id: int, metric_id: int, limit: int) -> List[TelemetryPoint]:
        response = await self.repository.get_history(satellite_id, metric_id, limit)
        return [
            TelemetryPoint.model_validate(point)
            for point in response
        ]


