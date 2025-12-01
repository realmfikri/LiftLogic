# LiftLogic

LiftLogic is an elevator dispatch simulator with a FastAPI backend and a React dashboard for real-time visualization, control, and analytics.

## Project overview
- **Simulation core**: Models a high-rise building, elevators, passengers, and schedulers (FCFS, SCAN, destination dispatch).
- **API layer**: Exposes the simulation via REST/WebSocket for live telemetry, algorithm switches, passenger injections, and elevator availability.
- **Dashboard**: Visualizes elevator positions and queues, streams metrics, and provides controls for burst testing and service toggles.
- **Offline scenarios**: Reusable JSON configs enable reproducible runs for benchmarking scheduling strategies.

## Architecture
```mermaid
graph TD
    UI[React dashboard] -->|WebSocket: /ws/stream\nREST: /state, /algorithm, /passengers/spawn| API[FastAPI server]
    API --> Manager[SimulationManager]
    Manager --> Sim[Simulation]
    Sim --> Build[Building]
    Build --> Elevators[Elevators]
    Build --> Floors[Floors]
    Sim --> Metrics[Metrics tracker]
    Build --> Schedulers[Schedulers (FCFS/SCAN/Destination Dispatch)]
```

Key data flow:
1. Dashboard subscribes to `/ws/stream` for real-time state snapshots and posts commands to REST endpoints.
2. `SimulationManager` steps the core simulation on a configurable tick interval, rebroadcasting building and metrics snapshots.
3. The `Building` uses pluggable schedulers to assign targets to elevators based on floor queues and constraints.
4. Metrics (wait/ride percentiles, throughput) are computed continuously for visualization and offline comparisons.

## Setup
### Python API & simulator
1. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the simulation API (FastAPI + WebSocket):
   ```bash
   PYTHONPATH=src uvicorn server.app:app --reload
   ```
3. The API serves on `http://127.0.0.1:8000` by default.

### React dashboard
1. Install dependencies:
   ```bash
   cd web
   npm install
   ```
2. Launch the dashboard:
   ```bash
   npm run dev
   ```
3. Open the printed localhost URL (typically `http://localhost:5173`) to view live elevator positions, metrics, and controls.

## Usage examples
### Running the live simulator + UI
- Start the API and dashboard as shown above; the UI will stream state, let you switch algorithms, spawn passenger bursts, and toggle elevator availability.

### Running offline scenarios
Use the JSON configs in `configs/` with the CLI helper to benchmark schedulers without the UI:
```bash
PYTHONPATH=src python scripts/run_scenario.py configs/morning_rush.json --output results/morning_rush.json
PYTHONPATH=src python scripts/run_scenario.py configs/normal_traffic.json
PYTHONPATH=src python scripts/run_scenario.py configs/elevator_outage_drill.json --output results/outage.json
```
The script prints final metrics and, if `--output` is provided, writes snapshots for plotting or diffing between runs.

### Comparing scenarios
1. Run multiple configs with `--output` into a `results/` directory.
2. Compare aggregated stats (average wait, p95 wait/ride, throughput) across files, or visualize `metrics_over_time` to see scheduler stability under different loads.
3. Swap the scheduler in a config (e.g., `fcfs` vs `scan`) to quantify dispatch improvements while keeping traffic identical.

## Scenario catalog (`configs/`)
- `morning_rush.json`: Heavy lobby-to-office surge with focused destinations using the SCAN scheduler.
- `normal_traffic.json`: Balanced weekday traffic under FCFS for a baseline.
- `elevator_outage_drill.json`: Schedules elevator outages mid-run while destination dispatch balances remaining capacity.

## Contribution guidelines
See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, coding standards, and testing expectations.

## Roadmap
Planned milestones for testing depth and performance tracking live in [ROADMAP.md](ROADMAP.md).
