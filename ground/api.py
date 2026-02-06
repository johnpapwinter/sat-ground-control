from datetime import datetime
from typing import List

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis

from ground_commander import send_command

app = FastAPI()

r = Redis(host='localhost', port=6379, db=0)

class TelemetryPoint(BaseModel):
    timestamp: datetime
    value: float


class CommandPoint(BaseModel):
    opcode: int
    frequency: float



@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool("postgres://postgres:space@localhost:5432/space")

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()


@app.get("/satellite/{sat_id}/realtime")
async def get_realtime_status(sat_id: int):
    """Get the absolute latest data from Redis (Hot Path)"""
    return {
        "satellite_id": sat_id,
        "voltage": r.get(f"sat:{sat_id}:voltage"),
        "temperature": r.get(f"sat:{sat_id}:temperature"),
        "last_contact": r.get(f"sat:{sat_id}:last_contact")
    }

@app.get("/satellite/{sat_id}/history", response_model=List[TelemetryPoint])
async def get_history(sat_id: int, metric_id: int, limit: int = 100):
    """Get historical trends from TimescaleDB (Cold Path)"""
    query = """
        SELECT timestamp, value 
        FROM telemetry 
        WHERE satellite_id = $1 AND metric_id = $2
        ORDER BY timestamp DESC 
        LIMIT $3
    """
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(query, sat_id, metric_id, limit)
        return [{"timestamp": row['timestamp'], "value": row['value']} for row in rows]

@app.post("/satellite/command")
async def set_sat_command(command: CommandPoint):
    try:
        send_command(command.opcode, command.frequency)
        return {"status": "Command Sent", "opcode": command.opcode, "param": command.frequency}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


