# TrainHub backend

FastAPI + PostgreSQL + asyncpg (raw parameterized SQL). No ORM.

## Run locally

```bash
cd backend
cp .env.example .env
docker compose up -d postgres redis
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.db.migrate
python scripts/seed_admin.py
uvicorn app.main:app --reload --app-dir .
```

- Swagger: http://127.0.0.1:8009/docs
- Health: http://127.0.0.1:8009/health
- Media files: `backend/media/` → http://127.0.0.1:8009/media/...
- App API: `/api/v1/app/...`
- Admin API: `/api/v1/admin/...`

Dev admin (from `.env.example`): `admin@trainhub.local` / `ChangeMeAdmin1`

## Tests

```bash
pytest
```
