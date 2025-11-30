from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .building import Building
from .passenger import Passenger


@dataclass
class MorningRushWindow:
    start_time: int
    end_time: int
    multiplier: float
    origin_floor: int = 0
    destination_focus: Optional[int] = None

    def active(self, time_step: int, origin: int) -> bool:
        return self.start_time <= time_step < self.end_time and origin == self.origin_floor


@dataclass
class MetricsSnapshot:
    time_step: int
    average_wait: float
    wait_p95: float
    average_ride: float
    ride_p95: float
    throughput: int


class MetricsTracker:
    def __init__(self) -> None:
        self.wait_times: List[int] = []
        self.ride_times: List[int] = []
        self.throughput: int = 0

    def record_wait_time(self, passenger: Passenger) -> None:
        if passenger.wait_time is not None:
            self.wait_times.append(passenger.wait_time)

    def record_ride_time(self, passenger: Passenger) -> None:
        if passenger.ride_time is not None:
            self.ride_times.append(passenger.ride_time)
            self.throughput += 1

    def _average(self, values: List[int]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _percentile(self, values: List[int], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * percentile
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_vals[int(k)])
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return float(d0 + d1)

    def snapshot(self, time_step: int) -> MetricsSnapshot:
        return MetricsSnapshot(
            time_step=time_step,
            average_wait=self._average(self.wait_times),
            wait_p95=self._percentile(self.wait_times, 0.95),
            average_ride=self._average(self.ride_times),
            ride_p95=self._percentile(self.ride_times, 0.95),
            throughput=self.throughput,
        )


class Simulation:
    """Time-stepped elevator simulation for analytics and UI consumption."""

    def __init__(
        self,
        building: Building,
        arrival_rate_per_floor: float = 0.1,
        morning_bursts: Optional[List[MorningRushWindow]] = None,
        random_seed: Optional[int] = None,
        metrics_hook_interval: int = 1,
    ) -> None:
        self.building = building
        self.arrival_rate_per_floor = arrival_rate_per_floor
        self.morning_bursts = morning_bursts or []
        self.random = random.Random(random_seed)
        self.current_time: int = 0
        self.metrics = MetricsTracker()
        self.event_hooks: Dict[str, List[Callable[[object], None]]] = {}
        self.metrics_hook_interval = max(1, metrics_hook_interval)
        self._next_passenger_id = 0

    def run(self, duration: int) -> None:
        for _ in range(duration):
            self.step()

    def step(self) -> None:
        self._generate_passenger_arrivals()
        self.building.dispatch(self.current_time)
        for elevator in self.building.elevators:
            elevator.step(self.building, self.current_time, self.metrics)

        if self.current_time % self.metrics_hook_interval == 0:
            self._emit_metrics()

        self.current_time += 1

    def on_event(self, event: str, callback: Callable[[object], None]) -> None:
        self.event_hooks.setdefault(event, []).append(callback)

    def trigger_elevator_fault(self, elevator_id: int, reason: Optional[str] = None) -> None:
        elevator = self._get_elevator(elevator_id)
        if not elevator:
            return
        elevator.trigger_fault(reason)
        self._emit("fault", {"elevator_id": elevator_id, "reason": reason, "time": self.current_time})

    def start_maintenance(self, elevator_id: int) -> None:
        elevator = self._get_elevator(elevator_id)
        if not elevator:
            return
        elevator.start_maintenance()
        self._emit("maintenance", {"elevator_id": elevator_id, "time": self.current_time})

    def restore_elevator(self, elevator_id: int) -> None:
        elevator = self._get_elevator(elevator_id)
        if not elevator:
            return
        elevator.restore_service()
        self._emit("restore", {"elevator_id": elevator_id, "time": self.current_time})

    def _generate_passenger_arrivals(self) -> None:
        total_arrivals = 0
        for floor in self.building.floors:
            multiplier = self._burst_multiplier(floor.number)
            arrivals = self._poisson(self.arrival_rate_per_floor * multiplier)
            total_arrivals += arrivals
            for _ in range(arrivals):
                destination = self._choose_destination(floor.number)
                passenger = Passenger(
                    passenger_id=self._next_passenger_id,
                    origin=floor.number,
                    destination=destination,
                    arrival_time=self.current_time,
                )
                self._next_passenger_id += 1
                floor.add_passenger(passenger)
                self.building.request_pickup(floor.number, passenger.direction)
        if total_arrivals:
            self._emit("arrival", {"time": self.current_time, "count": total_arrivals})

    def _choose_destination(self, origin: int) -> int:
        possible_floors = [f for f in range(self.building.num_floors) if f != origin]
        active_burst = next((b for b in self.morning_bursts if b.active(self.current_time, origin)), None)
        if active_burst and active_burst.destination_focus is not None:
            return active_burst.destination_focus
        return self.random.choice(possible_floors)

    def _burst_multiplier(self, origin: int) -> float:
        for burst in self.morning_bursts:
            if burst.active(self.current_time, origin):
                return burst.multiplier
        return 1.0

    def _poisson(self, lam: float) -> int:
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= self.random.random()
        return k - 1

    def _emit_metrics(self) -> None:
        snapshot = self.metrics.snapshot(self.current_time)
        self._emit("metrics", {"metrics": snapshot, "building": self.building.snapshot()})

    def _emit(self, event: str, payload: object) -> None:
        for callback in self.event_hooks.get(event, []):
            callback(payload)

    def _get_elevator(self, elevator_id: int):
        for elevator in self.building.elevators:
            if elevator.elevator_id == elevator_id:
                return elevator
        return None
