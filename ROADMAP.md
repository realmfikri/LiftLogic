# LiftLogic Roadmap

## Near-term
- Harden scheduler selection APIs and expose scheduler metadata over `/state` for UI introspection.
- Expand scenario catalog with mixed-mode traffic (lunch rush, fire drill, service-elevator-only).
- Add baseline plots for wait/ride percentiles per scheduler to guide tuning.

## Testing milestones
- **Unit**: Increase coverage for `scheduler` implementations (FCFS/SCAN/destination dispatch) and passenger queue transitions.
- **Integration**: Add FastAPI tests that validate algorithm switching, passenger batch injections, and elevator availability toggles end-to-end.
- **UI/system**: Smoke test the React dashboard against a running API, ensuring WebSocket reconnects and control panel actions update state.

## Performance benchmarks
- Automate weekly runs of `scripts/run_scenario.py` for `configs/morning_rush.json`, `configs/normal_traffic.json`, and `configs/elevator_outage_drill.json`.
- Track average and p95 wait/ride times plus throughput deltas for scheduler changes; flag regressions >5%.
- Profile heavy scenarios (morning rush + outages) to spot bottlenecks in scheduler selection and elevator stepping.
