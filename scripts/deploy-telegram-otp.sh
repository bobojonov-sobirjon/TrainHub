#!/bin/bash
set -euo pipefail
APP=/var/www/trainhub
SRC=/tmp/th-tg
cp -f "$SRC/010_telegram_profiles.sql" "$APP/backend/migrations/010_telegram_profiles.sql"
cp -f "$SRC/auth_schema.py" "$APP/backend/app/schemas/auth.py"
cp -f "$SRC/telegram_auth.py" "$APP/backend/app/services/telegram_auth.py"
cp -f "$SRC/auth_api.py" "$APP/backend/app/api/app/auth.py"
cp -f "$SRC/main.py" "$APP/backend/app/main.py"
cp -f "$SRC/redis.py" "$APP/backend/app/deps/redis.py"
chown trainhub:www-data \
  "$APP/backend/migrations/010_telegram_profiles.sql" \
  "$APP/backend/app/schemas/auth.py" \
  "$APP/backend/app/services/telegram_auth.py" \
  "$APP/backend/app/api/app/auth.py" \
  "$APP/backend/app/main.py" \
  "$APP/backend/app/deps/redis.py"
chmod 640 \
  "$APP/backend/migrations/010_telegram_profiles.sql" \
  "$APP/backend/app/schemas/auth.py" \
  "$APP/backend/app/services/telegram_auth.py" \
  "$APP/backend/app/api/app/auth.py" \
  "$APP/backend/app/main.py" \
  "$APP/backend/app/deps/redis.py"
sudo -u trainhub bash -c "cd '$APP/backend' && .venv/bin/python -m app.db.migrate"
systemctl restart trainhub-api
sleep 2
systemctl is-active trainhub-api
curl -fsS http://127.0.0.1:8005/openapi.json | python3 -c "import json,sys; p=json.load(sys.stdin)['paths'];
print([k for k in p if 'telegram' in k])
print(p['/api/v1/app/auth/telegram/send-code']['post']['tags'])
print(p['/api/v1/app/auth/telegram/verify']['post']['tags'])"
echo DONE
