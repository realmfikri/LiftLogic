from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import asdict
from typing import Dict, Optional, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from simulation import Building, Elevator, Simulation


class AlgorithmSelection(BaseModel):
    name: str
    options: Dict[str, object] = {}


class SpawnBatchRequest(BaseModel):
    origin: int
    count: int = 25
    destination: Optional[int] = None


class AvailabilityUpdate(BaseModel):
    available: bool
    reason: Optional[str] = None


class SimulationManager:
    def __init__(self, num_floors: int = 100, elevator_count: int = 10, tick_interval: float = 0.25) -> None:
        elevators = [Elevator(i) for i in range(elevator_count)]
        building = Building(num_floors=num_floors, elevators=elevators)
        self.simulation = Simulation(
            building=building,
            arrival_rate_per_floor=0.05,
            metrics_hook_interval=1,
        )
        self.tick_interval = tick_interval
        self.clients: Set[WebSocket] = set()
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            async with self._lock:
                self.simulation.step()
                payload = self.current_state()
            await self.broadcast(payload)
            await asyncio.sleep(self.tick_interval)

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload)
        disconnected: Set[WebSocket] = set()
        for client in set(self.clients):
            try:
                await client.send_text(message)
            except WebSocketDisconnect:
                disconnected.add(client)
        for client in disconnected:
            await self.unregister(client)

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)
        await websocket.send_text(json.dumps(self.current_state()))

    async def unregister(self, websocket: WebSocket) -> None:
        if websocket in self.clients:
            self.clients.remove(websocket)
        with contextlib.suppress(Exception):
            await websocket.close()

    def current_state(self) -> dict:
        metrics = asdict(self.simulation.metrics.snapshot(self.simulation.current_time))
        return {
            "time": self.simulation.current_time,
            "building": self.simulation.building.snapshot(),
            "metrics": metrics,
            "scheduler": self.simulation.building.scheduler_name,
        }

    async def set_scheduler(self, name: str, options: Dict[str, object]) -> dict:
        async with self._lock:
            self.simulation.building.set_scheduler(name, **options)
            return self.current_state()

    async def spawn_batch(self, origin: int, count: int, destination: Optional[int]) -> dict:
        async with self._lock:
            spawned = self.simulation.spawn_passenger_batch(origin, count, destination)
            state = self.current_state()
            state["spawned"] = spawned
            return state

    async def set_availability(self, elevator_id: int, available: bool, reason: Optional[str]) -> dict:
        async with self._lock:
            if available:
                self.simulation.restore_elevator(elevator_id)
            else:
                self.simulation.start_maintenance(elevator_id)
            state = self.current_state()
            state["elevator_id"] = elevator_id
            state["available"] = available
            state["reason"] = reason
            return state


manager = SimulationManager()
app = FastAPI(title="LiftLogic Simulation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await manager.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await manager.stop()


@app.get("/state")
async def get_state() -> dict:
    return manager.current_state()


@app.post("/algorithm")
async def set_algorithm(selection: AlgorithmSelection) -> dict:
    try:
        return await manager.set_scheduler(selection.name, selection.options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/passengers/spawn")
async def spawn_batch(request: SpawnBatchRequest) -> dict:
    return await manager.spawn_batch(request.origin, request.count, request.destination)


@app.post("/elevators/{elevator_id}/availability")
async def update_availability(elevator_id: int, availability: AvailabilityUpdate) -> dict:
    return await manager.set_availability(elevator_id, availability.available, availability.reason)


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.unregister(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)
