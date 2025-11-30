from __future__ import annotations

from math import sqrt
from typing import Iterable, List

from .interface import ElevatorSnapshot, PendingRequest


def estimate_travel_time(elevator: ElevatorSnapshot, floor: int) -> float:
    """Estimate time to reach a floor using cruise speed and acceleration.

    The calculation approximates a trapezoidal velocity profile with
    acceleration and deceleration phases. If acceleration is zero, the
    estimate falls back to simple distance / speed.
    """

    distance = abs(elevator.position - floor)
    if distance == 0:
        return 0

    if elevator.acceleration <= 0 or elevator.cruise_speed <= 0:
        return distance / elevator.cruise_speed if elevator.cruise_speed > 0 else float("inf")

    time_to_cruise = elevator.cruise_speed / elevator.acceleration
    distance_to_cruise = 0.5 * elevator.acceleration * time_to_cruise**2
    if 2 * distance_to_cruise >= distance:
        # Triangular profile: accelerate half-way then decelerate
        return 2 * sqrt(distance / elevator.acceleration)

    cruise_distance = distance - 2 * distance_to_cruise
    cruise_time = cruise_distance / elevator.cruise_speed
    return 2 * time_to_cruise + cruise_time


def sort_requests_in_direction(requests: Iterable[PendingRequest], direction: int) -> List[PendingRequest]:
    """Sort requests to mirror SCAN behavior for a given direction."""

    key = (lambda req: req.origin) if direction >= 0 else (lambda req: -req.origin)
    return sorted(requests, key=key)
