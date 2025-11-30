from __future__ import annotations

from typing import Dict, Type

from .destination_dispatch import DestinationDispatchScheduler
from .fcfs import FirstComeFirstServedScheduler
from .interface import ElevatorSnapshot, PendingRequest, Scheduler
from .scan import ScanScheduler

__all__ = [
    "DestinationDispatchScheduler",
    "FirstComeFirstServedScheduler",
    "ScanScheduler",
    "Scheduler",
    "get_scheduler",
]


SCHEDULER_REGISTRY: Dict[str, Type[Scheduler]] = {
    "fcfs": FirstComeFirstServedScheduler,
    "scan": ScanScheduler,
    "destination_dispatch": DestinationDispatchScheduler,
}


def get_scheduler(name: str, **kwargs) -> Scheduler:
    cls = SCHEDULER_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown scheduler '{name}'. Available: {', '.join(SCHEDULER_REGISTRY)}")
    return cls(**kwargs)
