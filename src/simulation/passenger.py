from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Passenger:
    """Represents a rider moving between floors."""

    passenger_id: int
    origin: int
    destination: int
    arrival_time: int
    board_time: Optional[int] = None
    alight_time: Optional[int] = None
    metadata: dict = field(default_factory=dict)

    @property
    def direction(self) -> int:
        """Return +1 for up, -1 for down."""
        return 1 if self.destination > self.origin else -1

    def record_boarding(self, time_step: int) -> None:
        self.board_time = time_step

    def record_alighting(self, time_step: int) -> None:
        self.alight_time = time_step

    @property
    def wait_time(self) -> Optional[int]:
        if self.board_time is None:
            return None
        return self.board_time - self.arrival_time

    @property
    def ride_time(self) -> Optional[int]:
        if self.board_time is None or self.alight_time is None:
            return None
        return self.alight_time - self.board_time
