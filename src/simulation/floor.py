from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List

from .passenger import Passenger


@dataclass
class Floor:
    """Represents a floor with directional queues."""

    number: int
    up_queue: Deque[Passenger] = field(default_factory=deque)
    down_queue: Deque[Passenger] = field(default_factory=deque)

    def add_passenger(self, passenger: Passenger) -> None:
        if passenger.direction > 0:
            self.up_queue.append(passenger)
        else:
            self.down_queue.append(passenger)

    def has_waiting(self) -> bool:
        return bool(self.up_queue or self.down_queue)

    def board_passengers(self, direction: int, capacity: int) -> List[Passenger]:
        queue = self.up_queue if direction > 0 else self.down_queue
        boarded: List[Passenger] = []
        while queue and len(boarded) < capacity:
            boarded.append(queue.popleft())
        return boarded

    def __len__(self) -> int:  # pragma: no cover - convenience
        return len(self.up_queue) + len(self.down_queue)
