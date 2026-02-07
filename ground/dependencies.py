from fastapi.params import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ground.redis_client import get_redis
from ground.telemetry_repository import TelemetryRepository
from ground.telemetry_service import TelemetryService
from ground.timescale_client import get_timescale_db


def inject_telemetry_repository(timescale_db: AsyncSession = Depends(get_timescale_db),
                                redis_db: Redis = Depends(get_redis)
) -> TelemetryRepository:
    return TelemetryRepository(timescale_db, redis_db)


def inject_telemetry_service(repository: TelemetryRepository = Depends(inject_telemetry_repository)
) -> TelemetryService:
    return TelemetryService(repository)

