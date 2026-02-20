from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.params import Depends

from ground.api.dependencies import inject_telemetry_service
from ground.api.schemas import CommandPoint, TelemetryPoint, LastStatus
from ground.api.telemetry_service import TelemetryService

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
async def set_sat_command(
        command: CommandPoint,
        service: TelemetryService = Depends(inject_telemetry_service)
):
    try:
        await service.push_command(command)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


