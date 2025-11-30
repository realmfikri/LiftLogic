from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from .interface import ElevatorSnapshot, PendingRequest, Scheduler
from .utils import estimate_travel_time


class DestinationDispatchScheduler:
    """Groups passengers by destination clusters for a dispatch cycle."""

    def __init__(self, cluster_size: int = 3) -> None:
        self.cluster_size = max(1, cluster_size)

    def select_calls(
        self,
        elevator_state: Iterable[ElevatorSnapshot],
        pending_requests: Iterable[PendingRequest],
    ) -> Dict[int, List[int]]:
        assignments: Dict[int, List[int]] = {}
        elevators = list(elevator_state)
        clusters = self._cluster_requests(pending_requests)

        for cluster_key, grouped_requests in clusters:
            chosen = self._best_elevator(elevators, grouped_requests)
            if chosen is None:
                continue
            targets = assignments.setdefault(chosen.elevator_id, [])
            for request in grouped_requests:
                if request.origin not in targets:
                    targets.append(request.origin)
                # Pre-seed likely destination stops to keep riders together
                for destination in self._cluster_destinations(request.destinations):
                    if destination not in targets:
                        targets.append(destination)
        return assignments

    def _cluster_requests(
        self, pending_requests: Iterable[PendingRequest]
    ) -> List[Tuple[int, List[PendingRequest]]]:
        buckets: Dict[int, List[PendingRequest]] = defaultdict(list)
        for request in pending_requests:
            bucket = self._destination_bucket(request.destinations)
            buckets[bucket].append(request)
        return list(buckets.items())

    def _destination_bucket(self, destinations: List[int]) -> int:
        if not destinations:
            return 0
        focus = int(sum(destinations) / len(destinations))
        return focus // self.cluster_size

    def _cluster_destinations(self, destinations: List[int]) -> List[int]:
        if not destinations:
            return []
        destinations = sorted(set(destinations))
        clustered: List[int] = []
        current_cluster: List[int] = []
        for destination in destinations:
            if not current_cluster:
                current_cluster.append(destination)
                continue
            if destination - current_cluster[0] < self.cluster_size:
                current_cluster.append(destination)
            else:
                clustered.append(int(sum(current_cluster) / len(current_cluster)))
                current_cluster = [destination]
        if current_cluster:
            clustered.append(int(sum(current_cluster) / len(current_cluster)))
        return clustered

    def _best_elevator(
        self, elevators: List[ElevatorSnapshot], requests: List[PendingRequest]
    ) -> ElevatorSnapshot | None:
        if not requests:
            return None
        required_capacity = sum(req.passenger_count for req in requests)
        feasible = [e for e in elevators if e.available_capacity >= required_capacity]
        if not feasible:
            feasible = [e for e in elevators if e.available_capacity > 0]
        if not feasible:
            return None
        centroid_floor = int(
            sum(req.origin for req in requests) / len(requests)
        )
        feasible.sort(
            key=lambda e: (
                estimate_travel_time(e, centroid_floor) + e.door_dwell,
                len(e.targets),
            )
        )
        return feasible[0]
