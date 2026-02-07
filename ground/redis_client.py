from typing import AsyncGenerator

import redis

pool = redis.ConnectionPool.from_url("redis://localhost:6379/0", decode_responses=True)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.close()

