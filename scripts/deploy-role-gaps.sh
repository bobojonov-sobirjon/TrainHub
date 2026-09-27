#!/bin/bash
set -euo pipefail
APP=/var/www/trainhub
SRC=/tmp/th-role
BACKEND="${APP}/backend"
ADMIN="${APP}/admin-panel"

echo "==> copy backend"
mkdir -p "${BACKEND}/app/core" "${BACKEND}/app/schemas" "${BACKEND}/app/services" \
  "${BACKEND}/app/api/app" "${BACKEND}/app/api/admin" "${BACKEND}/app/sql/users" \
  "${BACKEND}/app/sql/auth" "${BACKEND}/migrations"

cp -a "${SRC}/backend/app/." "${BACKEND}/app/"
cp -f "${SRC}/backend/migrations/011_role_gaps.sql" "${BACKEND}/migrations/011_role_gaps.sql"

echo "==> copy admin src"
mkdir -p "${ADMIN}/src"
cp -a "${SRC}/admin-panel/src/." "${ADMIN}/src/"

chown -R trainhub:www-data "${BACKEND}/app" "${BACKEND}/migrations/011_role_gaps.sql" "${ADMIN}/src"
find "${BACKEND}/app" -type d -exec chmod 750 {} \;
find "${BACKEND}/app" -type f -exec chmod 640 {} \;
chmod 640 "${BACKEND}/migrations/011_role_gaps.sql"
find "${ADMIN}/src" -type d -exec chmod 750 {} \;
find "${ADMIN}/src" -type f -exec chmod 640 {} \;

echo "==> migrate"
sudo -u trainhub bash -c "cd '${BACKEND}' && .venv/bin/python -m app.db.migrate"

echo "==> restart api"
systemctl restart trainhub-api
sleep 2
systemctl is-active trainhub-api
curl -fsS http://127.0.0.1:8005/health
echo

echo "==> admin build"
if [ -f /root/trainhub-credentials.txt ]; then
  # keep existing admin .env
  true
fi
sudo -u trainhub bash -c "cd '${ADMIN}' && npm install && npm run build"
chown -R trainhub:www-data "${ADMIN}/dist"
find "${ADMIN}/dist" -type d -exec chmod 750 {} \;
find "${ADMIN}/dist" -type f -exec chmod 640 {} \;
systemctl reload nginx

echo "==> verify tags"
curl -fsS http://127.0.0.1:8005/openapi.json | python3 -c "
import json,sys
spec=json.load(sys.stdin)
tags=sorted({t for p in spec['paths'].values() for op in p.values() if isinstance(op,dict) for t in op.get('tags',[])})
print('TAGS', [t for t in tags if t.startswith('Client') or t.startswith('Coach')])
p=spec['paths']
print('client/home', p['/api/v1/app/client/home']['get']['tags'])
print('trainer/clients', p['/api/v1/app/trainer/clients']['get']['tags'])
print('patch/me', 'patch' in p['/api/v1/app/me'])
"
echo DONE
