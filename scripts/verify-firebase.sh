#!/bin/bash
set -euo pipefail
cd /var/www/trainhub/backend
sudo -u trainhub .venv/bin/python - <<'PY'
from app.core.config import settings
from app.services.firebase import init_firebase, is_configured
print("project", settings.firebase_project_id)
print("configured", is_configured())
print("init", init_firebase())
PY
curl -fsS http://127.0.0.1:8005/health
echo
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8005/docs
systemctl is-active trainhub-api
