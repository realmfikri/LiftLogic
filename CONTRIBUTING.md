# Contributing to LiftLogic

Thank you for helping improve LiftLogic! This guide covers workflow, coding standards, and testing expectations.

## Workflow
- Fork or create a feature branch from `main`.
- Keep changes small and focused; prefer incremental pull requests.
- Update docs (README, configs, diagrams) when behavior or workflows change.
- When adding APIs or UI controls, document the endpoints and user flows.

## Coding standards
- **Python**: Type hints required; prefer small, pure functions where possible. Handle errors with informative messages—avoid silent failures. Keep imports sorted and avoid catching `Exception` unless necessary. Never wrap imports in `try/except`.
- **FastAPI**: Validate request bodies with Pydantic models and return descriptive HTTP errors. Keep WebSocket handlers resilient to disconnects.
- **React**: Favor functional components and hooks; keep state colocated. Use descriptive prop names and keep side effects inside `useEffect` hooks.
- **Testing mindset**: Write deterministic logic (seed RNGs in tests), isolate time-dependent calculations, and expose scheduler decisions for inspection.

## Testing expectations
- **Unit tests**: Cover scheduler selection logic, passenger flow calculations, and helpers with realistic edge cases.
- **Integration tests**: Exercise FastAPI endpoints (REST + WebSocket) and, where feasible, dashboard interactions or API/worker round-trips.
- **Performance baselines**: Capture metrics snapshots from `scripts/run_scenario.py` for common configs (morning rush, normal, outage drill) and track wait/ride p95 and throughput over time when optimizing algorithms.

## Commit hygiene
- Prefer clear, imperative commit messages (e.g., "Add outage drill scenario config").
- Rebase before opening a PR to keep history linear.
- Include testing notes in PR descriptions so reviewers can reproduce results quickly.
