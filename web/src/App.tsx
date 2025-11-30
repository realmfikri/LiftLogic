import { type FormEvent, useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";
const WS_URL = (() => {
  try {
    const url = new URL("/ws/stream", API_BASE);
    url.protocol = url.protocol.replace("http", "ws");
    return url.toString();
  } catch (err) {
    console.error("Invalid API_BASE", err);
    return "ws://localhost:8000/ws/stream";
  }
})();

interface ElevatorState {
  id: number;
  position: number;
  targets: number[];
  door_state: string;
  status: string;
  passenger_count: number;
}

interface FloorState {
  number: number;
  waiting_up: number;
  waiting_down: number;
  total_waiting: number;
}

interface MetricsSnapshot {
  time_step: number;
  average_wait: number;
  wait_p95: number;
  average_ride: number;
  ride_p95: number;
  throughput: number;
}

interface SimulationState {
  time: number;
  building: {
    floors: FloorState[];
    elevators: ElevatorState[];
  };
  metrics: MetricsSnapshot;
  scheduler: string;
  spawned?: number;
}

interface MetricsPoint {
  time: number;
  averageWait: number;
  throughput: number;
}

const schedulerOptions = [
  { value: "fcfs", label: "First Come, First Served" },
  { value: "scan", label: "SCAN (elevator SSTF)" },
  { value: "destination_dispatch", label: "Destination Dispatch" },
];

function gradientColor(ratio: number) {
  const clamped = Math.min(1, Math.max(0, ratio));
  const hue = 120 - clamped * 120; // green to red
  return `hsl(${hue}, 80%, ${40 + clamped * 10}%)`;
}

function buildSparkline(points: MetricsPoint[], width: number, height: number) {
  if (!points.length) return "";
  const max = Math.max(...points.map((p) => p.averageWait), 1);
  const min = 0;
  const xStep = width / Math.max(points.length - 1, 1);

  return points
    .map((point, idx) => {
      const x = idx * xStep;
      const y = height - ((point.averageWait - min) / (max - min)) * height;
      return `${idx === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function App() {
  const [state, setState] = useState<SimulationState | null>(null);
  const [history, setHistory] = useState<MetricsPoint[]>([]);
  const [connected, setConnected] = useState(false);
  const [batchOrigin, setBatchOrigin] = useState(0);
  const [batchDestination, setBatchDestination] = useState(50);
  const [batchSize, setBatchSize] = useState(50);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("fcfs");
  const [error, setError] = useState<string | null>(null);

  const floors = useMemo(() => {
    const floorList = state?.building.floors ?? [];
    return [...floorList].sort((a, b) => b.number - a.number);
  }, [state?.building.floors]);

  const elevators = state?.building.elevators ?? [];
  const maxWaiting = Math.max(...floors.map((f) => f.total_waiting), 1);
  const sparkline = buildSparkline(history.slice(-200), 220, 80);

  useEffect(() => {
    fetch(`${API_BASE}/state`)
      .then((res) => res.json())
      .then((data: SimulationState) => {
        setState(data);
        setSelectedAlgorithm(data.scheduler);
      })
      .catch((err) => setError(`Failed to fetch initial state: ${err}`));
  }, []);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError("WebSocket connection lost");
    ws.onmessage = (event) => {
      const payload: SimulationState = JSON.parse(event.data);
      setState(payload);
      setHistory((prev) => [
        ...prev.slice(-300),
        { time: payload.time, averageWait: payload.metrics.average_wait, throughput: payload.metrics.throughput },
      ]);
    };
    return () => ws.close();
  }, []);

  const updateAlgorithm = async (value: string) => {
    try {
      setSelectedAlgorithm(value);
      const res = await fetch(`${API_BASE}/algorithm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: value, options: {} }),
      });
      const data = await res.json();
      setState(data);
    } catch (err) {
      setError(`Failed to set algorithm: ${err}`);
    }
  };

  const spawnBatch = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/passengers/spawn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ origin: batchOrigin, destination: batchDestination, count: batchSize }),
      });
      const data = await res.json();
      setState(data);
    } catch (err) {
      setError(`Failed to spawn passengers: ${err}`);
    }
  };

  const toggleElevator = async (elevatorId: number, available: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/elevators/${elevatorId}/availability`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ available, reason: available ? "restore" : "manual" }),
      });
      const data = await res.json();
      setState(data);
    } catch (err) {
      setError(`Failed to toggle elevator: ${err}`);
    }
  };

  return (
    <div className="layout">
      <header>
        <div>
          <h1>LiftLogic Live Operations</h1>
          <p className="subtitle">100-floor visualization with real-time elevator telemetry and passenger heatmaps.</p>
        </div>
        <div className={`status ${connected ? "online" : "offline"}`}>
          {connected ? "Live" : "Offline"}
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="panes">
        <div className="controls">
          <section>
            <h3>Algorithm</h3>
            <select value={selectedAlgorithm} onChange={(e) => updateAlgorithm(e.target.value)}>
              {schedulerOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </section>

          <section>
            <h3>Spawn Passenger Batch</h3>
            <form className="spawn-form" onSubmit={spawnBatch}>
              <label>
                Origin floor
                <input type="number" min={0} max={99} value={batchOrigin} onChange={(e) => setBatchOrigin(Number(e.target.value))} />
              </label>
              <label>
                Destination floor
                <input
                  type="number"
                  min={0}
                  max={99}
                  value={batchDestination}
                  onChange={(e) => setBatchDestination(Number(e.target.value))}
                />
              </label>
              <label>
                Group size
                <input type="number" min={1} max={500} value={batchSize} onChange={(e) => setBatchSize(Number(e.target.value))} />
              </label>
              <button type="submit">Spawn riders</button>
            </form>
          </section>

          <section>
            <h3>Elevator Availability</h3>
            <div className="elevator-grid">
              {elevators.map((elevator) => (
                <div key={elevator.id} className="elevator-card">
                  <div className="elevator-id">Car {elevator.id + 1}</div>
                  <div className={`pill ${elevator.status === "in_service" ? "in-service" : "out-of-service"}`}>
                    {elevator.status.replace("_", " ")}
                  </div>
                  <button onClick={() => toggleElevator(elevator.id, elevator.status !== "in_service")}>
                    {elevator.status === "in_service" ? "Take out of service" : "Restore"}
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3>Live Metrics</h3>
            <div className="metric-row">
              <div>
                <div className="metric-label">Average wait</div>
                <div className="metric-value">{state ? state.metrics.average_wait.toFixed(1) : "-"} ticks</div>
              </div>
              <div>
                <div className="metric-label">Throughput</div>
                <div className="metric-value">{state ? state.metrics.throughput : "-"} riders</div>
              </div>
            </div>
            <svg className="sparkline" viewBox="0 0 220 80" preserveAspectRatio="none">
              <path d={sparkline} fill="none" stroke="#4ade80" strokeWidth={2} />
            </svg>
          </section>
        </div>

        <div className="visualization">
          <div className="sim-meta">
            <div>
              <strong>Tick:</strong> {state?.time ?? "-"}
            </div>
            <div>
              <strong>Algorithm:</strong> {state?.scheduler ?? "-"}
            </div>
            <div>
              <strong>Active elevators:</strong> {elevators.filter((e) => e.status === "in_service").length} / {elevators.length}
            </div>
          </div>

          <div className="building">
            <div className="shaft">
              {elevators.map((elevator) => (
                <div key={elevator.id} className="car" style={{ bottom: `${(100 * elevator.position) / 99}%` }}>
                  <div className="car-body">
                    <span>#{elevator.id + 1}</span>
                    <small>{elevator.passenger_count} pax</small>
                  </div>
                </div>
              ))}
            </div>

            <div className="floors">
              {floors.map((floor) => {
                const ratio = maxWaiting ? floor.total_waiting / maxWaiting : 0;
                const color = gradientColor(ratio);
                return (
                  <div key={floor.number} className="floor-row">
                    <div className="floor-label">{floor.number}</div>
                    <div className="heat" style={{ background: color, width: `${Math.min(100, ratio * 100)}%` }} />
                    <div className="queues">
                      <span>↑ {floor.waiting_up}</span>
                      <span>↓ {floor.waiting_down}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
