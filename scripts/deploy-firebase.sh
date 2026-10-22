#!/bin/bash
set -euo pipefail
APP=/var/www/trainhub
BACKEND="${APP}/backend"
ENV="${BACKEND}/.env"
FRAG=/tmp/trainhub-firebase.env

echo "==> git pull"
git config --global --add safe.directory "${APP}" || true
cd "${APP}"
git fetch --all
git reset --hard origin/main
git rev-parse --short HEAD

echo "==> merge FIREBASE_* into .env"
python3 - <<'PY'
from pathlib import Path
env_path = Path("/var/www/trainhub/backend/.env")
frag_path = Path("/tmp/trainhub-firebase.env")
if not frag_path.exists():
    raise SystemExit("missing /tmp/trainhub-firebase.env")
text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
if text.startswith("\ufeff"):
    text = text[1:]
lines = [ln for ln in text.splitlines() if not ln.startswith("FIREBASE_")]
while lines and lines[-1].strip() == "":
    lines.pop()
frag = frag_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
env_path.write_text("\n".join(lines) + "\n\n" + frag + "\n", encoding="utf-8")
print("firebase_keys", sum(1 for ln in frag.splitlines() if ln.startswith("FIREBASE_")))
PY
chown trainhub:www-data "${ENV}"
chmod 600 "${ENV}"
rm -f "${FRAG}"

echo "==> pip"
sudo -u trainhub bash -c "cd '${BACKEND}' && .venv/bin/pip install -q -r requirements.txt"

echo "==> migrate"
sudo -u trainhub bash -c "cd '${BACKEND}' && .venv/bin/python -m app.db.migrate"

echo "==> restart"
systemctl restart trainhub-api
sleep 3
systemctl is-active trainhub-api
curl -fsS http://127.0.0.1:8005/health
echo

echo "==> firebase check"
sudo -u trainhub bash -c "cd '${BACKEND}' && .venv/bin/python -c \"from app.core.config import settings; from app.services.firebase import init_firebase, is_configured; print('project', settings.firebase_project_id); print('configured', is_configured()); print('init', init_firebase())\""

echo DONE
