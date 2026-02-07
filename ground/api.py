from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.params import Depends

from ground.dependencies import inject_telemetry_service
from ground.schemas import CommandPoint, TelemetryPoint, LastStatus
from ground.telemetry_service import TelemetryService
from ground_commander import send_command

app = FastAPI()




@app.get("/satellite/{sat_id}/realtime", response_model=LastStatus)
async def get_realtime_status(
        sat_id: int,
        service: TelemetryService = Depends(inject_telemetry_service)
):
    """Get the absolute latest data from Redis (Hot Path)"""
    return service.get_realtime_status(sat_id)

@app.get("/satellite/{sat_id}/history", response_model=List[TelemetryPoint])
async def get_history(
        sat_id: int,
        metric_id: int,
        limit: int = 100,
        service: TelemetryService = Depends(inject_telemetry_service)
):
    """Get historical trends from TimescaleDB (Cold Path)"""
    return service.get_history(sat_id, metric_id, limit)

@app.post("/satellite/command")
async def set_sat_command(command: CommandPoint):
    try:
        send_command(command.opcode, command.frequency)
        return {"status": "Command Sent", "opcode": command.opcode, "param": command.frequency}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


