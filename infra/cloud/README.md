# FarmTwin Cloud Backend

FastAPI (Python 3.11) + PostgreSQL/TimescaleDB.

## Endpoints (planned)
- `POST /api/v1/surveys`          — ingest FTS JSON
- `POST /api/v1/surveys/kobo-ingest` — KoboToolbox webhook
- `GET  /api/v1/farms/{id}/status`— farm live status (Farmer PWA)
- `POST /api/v1/twin/assimilate`  — trigger EKF/EnKF update

See `docs/requirements.md §14` for full spec.
