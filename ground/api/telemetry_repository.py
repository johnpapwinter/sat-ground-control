from datetime import datetime, timezone
from typing import List

from redis.asyncio import Redis
from sqlalchemy import select, Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from ground.models import Telemetry


class TelemetryRepository:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def save_telemetry(self, satellite_id: int, metric_id: int, value: float) -> None:
        now = datetime.now(timezone.utc)

        metric_name = "voltage" if metric_id == 1 else "temperature"
        async with self.redis.pipeline() as pipe:
            await pipe.set(f"sat:{satellite_id}:{metric_name}", value)
            await pipe.set(f"sat:{satellite_id}:last_contact", now.isoformat())
            await pipe.execute()

        telemetry_entry = Telemetry(
            timestamp=now,
            satellite_id=satellite_id,
            metric_id=metric_id,
            value=value
        )
        self.db.add(telemetry_entry)
        await self.db.commit()

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


