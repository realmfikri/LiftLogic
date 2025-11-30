from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .elevator import Elevator
from .floor import Floor
from .config import ElevatorConstraints
from scheduler import ElevatorSnapshot, PendingRequest, Scheduler, get_scheduler


@dataclass
class Building:
    """Container for floors and elevators with simple dispatch."""

    num_floors: int
    elevators: List[Elevator] = field(default_factory=list)
    elevator_constraints: ElevatorConstraints = field(default_factory=ElevatorConstraints)
    scheduler_name: str = "fcfs"
    scheduler_options: dict = field(default_factory=dict)
    scheduler: Scheduler = field(init=False)
    floors: List[Floor] = field(init=False)

    def __post_init__(self) -> None:
        self.floors = [Floor(i) for i in range(self.num_floors)]
        self.scheduler = get_scheduler(self.scheduler_name, **self.scheduler_options)
        self._apply_constraints()

    def get_floor(self, floor_number: int) -> Optional[Floor]:
        if 0 <= floor_number < self.num_floors:
            return self.floors[floor_number]
        return None

    def request_pickup(self, floor_number: int, direction: int) -> Optional[Elevator]:
        # Requests are handled centrally by the scheduler during dispatch.
        return None

    def set_scheduler(self, name: str, **options) -> None:
        self.scheduler_name = name
        self.scheduler_options = options
        self.scheduler = get_scheduler(name, **options)

    def dispatch(self, current_time: int) -> None:
        requests = self._collect_pending_requests(current_time)
        snapshots = self._snapshot_elevators()
        assignments = self.scheduler.select_calls(snapshots, requests)
        for elevator_id, targets in assignments.items():
            elevator = self._get_elevator(elevator_id)
            if elevator is None:
                continue
            for target in targets:
                elevator.assign_target(target)

    def snapshot(self) -> dict:
        return {
            "floors": [len(floor) for floor in self.floors],
            "elevators": [
                {
                    "id": elevator.elevator_id,
                    "position": elevator.position,
                    "targets": list(elevator.targets),
                    "door_state": elevator.door_state,
                    "status": elevator.status,
                    "passenger_count": len(elevator.passengers),
                }
                for elevator in self.elevators
            ],
        }

    def _collect_pending_requests(self, current_time: int) -> List[PendingRequest]:
        requests: List[PendingRequest] = []
        for floor in self.floors:
            if floor.up_queue:
                requests.append(
                    PendingRequest(
                        origin=floor.number,
                        direction=1,
                        requested_at=floor.up_queue[0].arrival_time,
                        passenger_count=len(floor.up_queue),
                        destinations=[p.destination for p in floor.up_queue],
                    )
                )
            if floor.down_queue:
                requests.append(
                    PendingRequest(
                        origin=floor.number,
                        direction=-1,
                        requested_at=floor.down_queue[0].arrival_time,
                        passenger_count=len(floor.down_queue),
                        destinations=[p.destination for p in floor.down_queue],
                    )
                )
        return requests

    def _snapshot_elevators(self) -> List[ElevatorSnapshot]:
        return [
            ElevatorSnapshot(
                elevator_id=elevator.elevator_id,
                position=elevator.position,
                direction=elevator.direction,
                targets=list(elevator.targets),
                load=len(elevator.passengers),
                capacity=elevator.capacity,
                cruise_speed=elevator.speed_floors_per_tick,
                acceleration=elevator.acceleration_floors_per_tick2,
                door_dwell=elevator.door_dwell_ticks,
            )
            for elevator in self.elevators
            if elevator.in_service()
        ]

    def _apply_constraints(self) -> None:
        for elevator in self.elevators:
            elevator.capacity = self.elevator_constraints.capacity
            elevator.speed_floors_per_tick = (
                self.elevator_constraints.cruise_speed_floors_per_tick
            )
            elevator.acceleration_floors_per_tick2 = (
                self.elevator_constraints.acceleration_floors_per_tick2
            )
            elevator.door_dwell_ticks = self.elevator_constraints.door_dwell_ticks

    def _get_elevator(self, elevator_id: int) -> Optional[Elevator]:
        for elevator in self.elevators:
            if elevator.elevator_id == elevator_id:
                return elevator
        return None
