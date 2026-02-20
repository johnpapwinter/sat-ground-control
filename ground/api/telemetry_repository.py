import json

from redis.asyncio import Redis
from sqlalchemy import select, Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from ground.domain.models import Telemetry, CommandEntry


class TelemetryRepository:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def get_realtime_status(self, satellite_id: int) -> dict:
        keys = [f"sat:{satellite_id}:voltage", f"sat:{satellite_id}:temperature", f"sat:{satellite_id}:last_contact"]
        voltage, temperature, last_contact = await self.redis.mget(keys)

        return {
            "voltage": voltage,
            "temperature": temperature,
            "last_contact": last_contact
        }

    async def get_history(self, satellite_id: int, metric_id: int, limit: int = 100) -> Sequence[Telemetry]:
        statement = (
            select(Telemetry)
            .where(Telemetry.satellite_id == satellite_id)
            .where(Telemetry.metric_id == metric_id)
            .order_by(Telemetry.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(statement)
        return result.scalars().all()

    async def save_command(self, command: CommandEntry) -> CommandEntry:
        self.db.add(command)
        await self.db.commit()
        await self.db.refresh(command)
        return command

    async def push_to_queue(self, command: CommandEntry) -> None:
        queue_key = f"cmd_queue:{command.priority_level.value.lower()}"
        await self.redis.lpush(queue_key, json.dumps({
            "command_id": command.command_id,
            "opcode": command.opcode,
            "frequency": self._get_frequency(command),
        }))

    def _get_frequency(self, command: CommandEntry) -> str:
        return (command.command_payload.get("frequency")
                if isinstance(command.command_payload, dict)
                else json.loads(command.command_payload).get("frequency")
                )
