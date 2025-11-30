from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Protocol


@dataclass(frozen=True)
class ElevatorSnapshot:
    """Lightweight view of an elevator for scheduling decisions."""

    elevator_id: int
    position: float
    direction: int
    targets: List[int]
    load: int
    capacity: int
    cruise_speed: float
    acceleration: float
    door_dwell: int

    @property
    def available_capacity(self) -> int:
        return max(0, self.capacity - self.load)


@dataclass(frozen=True)
class PendingRequest:
    """Representation of a pending hall call for schedulers."""

    origin: int
    direction: int
    requested_at: int
    passenger_count: int
    destinations: List[int]


class Scheduler(Protocol):
    """Strategy interface for dispatching elevators to hall calls."""

    def select_calls(
        self,
        elevator_state: Iterable[ElevatorSnapshot],
        pending_requests: Iterable[PendingRequest],
    ) -> Dict[int, List[int]]:
        """
        Return mapping of elevator_id -> list of floor targets to service.

        Implementations may choose to batch requests or ignore some
        requests when no suitable elevator is available.
        """
        ...
