from __future__ import annotations

from typing import Dict, Iterable, List

from .interface import ElevatorSnapshot, PendingRequest, Scheduler
from .utils import estimate_travel_time, sort_requests_in_direction


class ScanScheduler:
    """Implements an elevator SCAN algorithm (elevator algorithm)."""

    def select_calls(
        self,
        elevator_state: Iterable[ElevatorSnapshot],
        pending_requests: Iterable[PendingRequest],
    ) -> Dict[int, List[int]]:
        assignments: Dict[int, List[int]] = {}
        elevators = list(elevator_state)
        requests = list(pending_requests)

        # Prioritize requests along current travel directions
        for elevator in elevators:
            direction = elevator.direction or 1
            in_path = [req for req in requests if self._is_in_path(elevator, req)]
            sorted_path = sort_requests_in_direction(in_path, direction)
            for request in sorted_path:
                if elevator.available_capacity <= 0:
                    break
                assignments.setdefault(elevator.elevator_id, []).append(request.origin)
                requests.remove(request)

        # Assign remaining requests to closest elevator respecting capacity
        for request in requests:
            candidate = self._closest_elevator(elevators, request)
            if candidate is None:
                continue
            assignments.setdefault(candidate.elevator_id, []).append(request.origin)
        return assignments

    def _is_in_path(self, elevator: ElevatorSnapshot, request: PendingRequest) -> bool:
        if elevator.direction == 0:
            return True
        return (elevator.direction > 0 and request.origin >= elevator.position) or (
            elevator.direction < 0 and request.origin <= elevator.position
        )

    def _closest_elevator(
        self, elevators: List[ElevatorSnapshot], request: PendingRequest
    ) -> ElevatorSnapshot | None:
        feasible = [e for e in elevators if e.available_capacity > 0]
        if not feasible:
            return None
        feasible.sort(
            key=lambda e: (
                estimate_travel_time(e, request.origin) + e.door_dwell,
                abs(e.direction - request.direction),
            )
        )
        return feasible[0]
