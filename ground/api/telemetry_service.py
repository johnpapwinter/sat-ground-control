import json
from datetime import datetime, timezone
from typing import List

from ground.api.schemas import LastStatus, TelemetryPoint, CommandPoint
from ground.api.telemetry_repository import TelemetryRepository
from ground.domain.enums import CommandState
from ground.domain.models import CommandEntry


class TelemetryService:
    def __init__(self, repository: TelemetryRepository):
        self.repository = repository

    async def get_realtime_status(self, satellite_id: int) -> LastStatus:
        response = await self.repository.get_realtime_status(satellite_id)
        return LastStatus(**response)

    async def get_history(self, satellite_id: int, metric_id: int, limit: int) -> List[TelemetryPoint]:
        response = await self.repository.get_history(satellite_id, metric_id, limit)
        return [
            TelemetryPoint.model_validate(point)
            for point in response
        ]

    async def push_command(self, command_dto: CommandPoint) -> None:
        command = CommandEntry(
            command_payload=json.dumps({"opcode": command_dto.opcode, "frequency": command_dto.frequency}),
            priority_level=command_dto.priority,
            state=CommandState.QUEUED,
            opcode=command_dto.opcode,
            timestamp=datetime.now(timezone.utc),
        )
        saved_command = await self.repository.save_command(command)
        await self.repository.push_to_queue(saved_command)



