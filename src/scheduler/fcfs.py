from __future__ import annotations

from typing import Dict, Iterable, List

from .interface import ElevatorSnapshot, PendingRequest, Scheduler
from .utils import estimate_travel_time


class FirstComeFirstServedScheduler:
    """Assigns elevators to the oldest outstanding requests."""

    def select_calls(
        self,
        elevator_state: Iterable[ElevatorSnapshot],
        pending_requests: Iterable[PendingRequest],
    ) -> Dict[int, List[int]]:
        assignments: Dict[int, List[int]] = {}
        elevators = list(elevator_state)
        open_requests = sorted(pending_requests, key=lambda req: req.requested_at)
        for request in open_requests:
            candidate = self._choose_elevator(elevators, request)
            if candidate is None:
                continue
            assignments.setdefault(candidate.elevator_id, []).append(request.origin)
            elevators = self._update_snapshot(elevators, candidate, request)
        return assignments

    def _choose_elevator(
        self, elevators: List[ElevatorSnapshot], request: PendingRequest
    ) -> ElevatorSnapshot | None:
        available = [e for e in elevators if e.available_capacity >= request.passenger_count]
        if not available:
            available = [e for e in elevators if e.available_capacity > 0]
        if not available:
            return None
        available.sort(
            key=lambda e: (
                estimate_travel_time(e, request.origin),
                len(e.targets),
                abs(e.direction - request.direction),
            )
        )
        return available[0]

    def _update_snapshot(
        self,
        elevators: List[ElevatorSnapshot],
        chosen: ElevatorSnapshot,
        request: PendingRequest,
    ) -> List[ElevatorSnapshot]:
        updated: List[ElevatorSnapshot] = []
        for elevator in elevators:
            if elevator.elevator_id == chosen.elevator_id:
                new_targets = list(elevator.targets)
                if request.origin not in new_targets:
                    new_targets.append(request.origin)
                updated.append(
                    ElevatorSnapshot(
                        elevator_id=elevator.elevator_id,
                        position=elevator.position,
                        direction=elevator.direction,
                        targets=new_targets,
                        load=elevator.load,
                        capacity=elevator.capacity,
                        cruise_speed=elevator.cruise_speed,
                        acceleration=elevator.acceleration,
                        door_dwell=elevator.door_dwell,
                    )
                )
            else:
                updated.append(elevator)
        return updated
