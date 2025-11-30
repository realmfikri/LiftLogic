from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from .passenger import Passenger

if TYPE_CHECKING:  # pragma: no cover - import cycle safe typing
    from .building import Building
    from .simulation import MetricsTracker


@dataclass
class Elevator:
    """A simple elevator controller with door and target handling."""

    elevator_id: int
    capacity: int
    speed_floors_per_tick: float = 1.0
    acceleration_floors_per_tick2: float = 0.0
    door_dwell_ticks: int = 1
    position: float = 0.0
    targets: List[int] = field(default_factory=list)
    passengers: List[Passenger] = field(default_factory=list)
    status: str = "in_service"  # in_service, faulted, maintenance
    door_state: str = "closed"
    _door_timer: int = 0
    _stop_handled: bool = False

    def in_service(self) -> bool:
        return self.status == "in_service"

    @property
    def direction(self) -> int:
        if not self.targets:
            return 0
        if self.position < self.targets[0]:
            return 1
        if self.position > self.targets[0]:
            return -1
        return 0

    def assign_target(self, floor: int) -> None:
        if floor not in self.targets:
            self.targets.append(floor)

    def step(self, building: "Building", current_time: int, metrics: "MetricsTracker") -> None:
        if not self.in_service():
            return

        if self.door_state == "open":
            if not self._stop_handled:
                self._handle_stop(building, current_time, metrics)
                self._stop_handled = True
            self._door_timer -= 1
            if self._door_timer <= 0:
                self.door_state = "closed"
            return

        if self.door_state != "closed":
            return

        if self.targets and self._should_stop_here(building):
            self._open_doors()
            self._stop_handled = False
            return

        self._move_towards_target()

        if self.targets and self._should_stop_here(building):
            self._open_doors()
            self._stop_handled = False

    def _should_stop_here(self, building: "Building") -> bool:
        at_floor = int(round(self.position))
        if self.targets and at_floor == self.targets[0]:
            return True
        floor = building.get_floor(at_floor)
        if floor is None:
            return False
        has_waiting = floor.has_waiting()
        has_dropoff = any(p.destination == at_floor for p in self.passengers)
        return has_waiting or has_dropoff

    def _move_towards_target(self) -> None:
        if not self.targets:
            return
        target = self.targets[0]
        if abs(self.position - target) <= self.speed_floors_per_tick:
            self.position = float(target)
            self.targets.pop(0)
        elif self.position < target:
            self.position += self.speed_floors_per_tick
        else:
            self.position -= self.speed_floors_per_tick

    def _open_doors(self) -> None:
        self.door_state = "open"
        self._door_timer = self.door_dwell_ticks

    def _handle_stop(self, building: "Building", current_time: int, metrics: "MetricsTracker") -> None:
        floor_number = int(round(self.position))
        floor = building.get_floor(floor_number)
        if floor is None:
            return

        # Alight
        remaining_passengers: List[Passenger] = []
        for passenger in self.passengers:
            if passenger.destination == floor_number:
                passenger.record_alighting(current_time)
                metrics.record_ride_time(passenger)
            else:
                remaining_passengers.append(passenger)
        self.passengers = remaining_passengers

        # Board
        free_space = self.capacity - len(self.passengers)
        direction = self.direction or 1
        boarded = floor.board_passengers(direction, free_space)
        for passenger in boarded:
            passenger.record_boarding(current_time)
            metrics.record_wait_time(passenger)
        self.passengers.extend(boarded)

        # Refresh targets
        if self.targets and self.targets[0] == floor_number:
            self.targets.pop(0)
        self.targets.extend(p.destination for p in boarded if p.destination not in self.targets)

    def trigger_fault(self, reason: Optional[str] = None) -> None:
        self.status = "faulted"
        self.targets.clear()
        self.door_state = "closed"

    def start_maintenance(self) -> None:
        self.status = "maintenance"
        self.targets.clear()
        self.door_state = "closed"

    def restore_service(self) -> None:
        self.status = "in_service"
