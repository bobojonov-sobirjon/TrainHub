#!/bin/bash
set -euo pipefail
APP_DIR=/var/www/trainhub
SRC=/tmp/th-media

cp -f "$SRC/007_exercise_photos.sql" "$APP_DIR/backend/migrations/007_exercise_photos.sql"
cp -f "$SRC/storage.py" "$APP_DIR/backend/app/services/storage.py"
cp -f "$SRC/catalog.py" "$APP_DIR/backend/app/services/catalog.py"
cp -f "$SRC/admin_programs.py" "$APP_DIR/backend/app/api/admin/programs.py"
cp -f "$SRC/stage.py" "$APP_DIR/backend/app/schemas/stage.py"
cp -f "$SRC/MediaFields.tsx" "$APP_DIR/admin-panel/src/components/MediaFields.tsx"
cp -f "$SRC/resources.ts" "$APP_DIR/admin-panel/src/api/resources.ts"
cp -f "$SRC/Exercises.tsx" "$APP_DIR/admin-panel/src/pages/Exercises.tsx"
cp -f "$SRC/ExerciseDetail.tsx" "$APP_DIR/admin-panel/src/pages/ExerciseDetail.tsx"
cp -f "$SRC/Programs.tsx" "$APP_DIR/admin-panel/src/pages/Programs.tsx"
cp -f "$SRC/ProgramDetail.tsx" "$APP_DIR/admin-panel/src/pages/ProgramDetail.tsx"
cp -f "$SRC/app.css" "$APP_DIR/admin-panel/src/styles/app.css"

sed -i 's|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=http://51.20.92.246|' "$APP_DIR/backend/.env"

chown -R trainhub:www-data "$APP_DIR/backend" "$APP_DIR/admin-panel"
sudo -u trainhub bash -c "cd '$APP_DIR/backend' && .venv/bin/python -m app.db.migrate"
sudo -u trainhub bash -c "cd '$APP_DIR/admin-panel' && npm install && npm run build"
rm -rf "$APP_DIR/admin-panel/node_modules"
find "$APP_DIR" -type d -exec chmod 750 {} \;
find "$APP_DIR" -type f -exec chmod 640 {} \;
chmod 600 "$APP_DIR/backend/.env"
chmod 770 "$APP_DIR/backend/media"
find "$APP_DIR/backend/.venv/bin" -type f -exec chmod 750 {} \;
systemctl restart trainhub-api
echo DONE
