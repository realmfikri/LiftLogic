"""CLI for running offline LiftLogic scenarios defined in JSON configs."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from simulation import Building, Elevator, ElevatorConstraints, MorningRushWindow, Simulation


def build_simulation(config: Dict) -> Simulation:
    building_cfg = config.get("building", {})
    num_floors = building_cfg.get("num_floors", 100)
    elevator_count = building_cfg.get("elevator_count", 10)
    constraints_cfg = building_cfg.get("constraints", {})
    constraints = ElevatorConstraints(**constraints_cfg)

    elevators = [Elevator(i) for i in range(elevator_count)]
    scheduler_cfg = config.get("scheduler", {})
    scheduler_name = scheduler_cfg.get("name", "fcfs")
    scheduler_options = scheduler_cfg.get("options", {})

    building = Building(
        num_floors=num_floors,
        elevators=elevators,
        elevator_constraints=constraints,
        scheduler_name=scheduler_name,
        scheduler_options=scheduler_options,
    )

    bursts = [
        MorningRushWindow(
            start_time=b.get("start_time", 0),
            end_time=b.get("end_time", 0),
            multiplier=b.get("multiplier", 1.0),
            origin_floor=b.get("origin_floor", 0),
            destination_focus=b.get("destination_focus"),
        )
        for b in config.get("morning_bursts", [])
    ]

    arrival_rate = config.get("arrival_rate_per_floor", 0.05)
    metrics_interval = config.get("metrics_hook_interval", 10)
    random_seed = config.get("random_seed")

    simulation = Simulation(
        building=building,
        arrival_rate_per_floor=arrival_rate,
        morning_bursts=bursts,
        random_seed=random_seed,
        metrics_hook_interval=metrics_interval,
    )
    return simulation


def _apply_scheduled_events(
    simulation: Simulation, events: Iterable[Dict], current_time: int
) -> None:
    for event in events:
        if event.get("type") != "outage":
            continue
        elevator_id = event.get("elevator_id")
        if elevator_id is None:
            continue
        if current_time == event.get("start_time"):
            simulation.start_maintenance(elevator_id)
        if current_time == event.get("end_time"):
            simulation.restore_elevator(elevator_id)


def run_simulation(simulation: Simulation, config: Dict) -> List[Dict]:
    duration = config.get("duration", 300)
    events = config.get("events", [])
    snapshots: List[Dict] = []

    for _ in range(duration):
        _apply_scheduled_events(simulation, events, simulation.current_time)
        simulation.step()
        if simulation.current_time % simulation.metrics_hook_interval == 0:
            metrics = asdict(simulation.metrics.snapshot(simulation.current_time))
            snapshots.append(metrics)
    return snapshots


def save_results(output_path: Optional[Path], data: Dict) -> None:
    if not output_path:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Path to a JSON scenario configuration file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path to write metrics snapshots as JSON",
    )
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    simulation = build_simulation(config)
    snapshots = run_simulation(simulation, config)

    final_metrics = asdict(simulation.metrics.snapshot(simulation.current_time))
    results = {
        "scenario": config.get("name", args.config.stem),
        "description": config.get("description"),
        "duration": config.get("duration", 300),
        "scheduler": config.get("scheduler", {}).get("name", "fcfs"),
        "final_metrics": final_metrics,
        "metrics_over_time": snapshots,
    }

    save_results(args.output, results)

    print(f"Scenario: {results['scenario']}")
    if results["description"]:
        print(results["description"])
    print(f"Scheduler: {results['scheduler']}")
    print(f"Duration: {results['duration']} ticks")
    print("Final metrics:")
    for key, value in final_metrics.items():
        print(f"  {key}: {value}")
    if args.output:
        print(f"Saved metrics to {args.output}")


if __name__ == "__main__":
    main()
