from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .elevator import Elevator
from .floor import Floor


@dataclass
class Building:
    """Container for floors and elevators with simple dispatch."""

    num_floors: int
    elevators: List[Elevator] = field(default_factory=list)
    floors: List[Floor] = field(init=False)

    def __post_init__(self) -> None:
        self.floors = [Floor(i) for i in range(self.num_floors)]

    def get_floor(self, floor_number: int) -> Optional[Floor]:
        if 0 <= floor_number < self.num_floors:
            return self.floors[floor_number]
        return None

    def request_pickup(self, floor_number: int, direction: int) -> Optional[Elevator]:
        elevator = self._select_elevator(floor_number)
        if elevator:
            elevator.assign_target(floor_number)
        return elevator

    def _select_elevator(self, floor_number: int) -> Optional[Elevator]:
        candidates = [e for e in self.elevators if e.in_service()]
        if not candidates:
            return None
        candidates.sort(key=lambda e: (abs(e.position - floor_number), len(e.targets)))
        return candidates[0]

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
