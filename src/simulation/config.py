from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ElevatorConstraints:
    """Physical constraints used by schedulers and controllers."""

    capacity: int = 8
    cruise_speed_floors_per_tick: float = 1.0
    acceleration_floors_per_tick2: float = 0.0
    door_dwell_ticks: int = 1
