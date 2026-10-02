#!/usr/bin/env bash
# Deploy the latest code from GitHub. Run on the server as the deploy user:
#   bash /srv/loveapp/app/deploy/update.sh
set -euo pipefail

APP_DIR=/srv/loveapp/app
VENV=/srv/loveapp/venv

cd "$APP_DIR"

echo "==> Pulling latest code"
git pull --ff-only

echo "==> Installing dependencies"
"$VENV/bin/pip" install --quiet -r loveapp/requirements.txt gunicorn

echo "==> Restarting service"
sudo systemctl restart loveapp
sleep 2

if systemctl is-active --quiet loveapp; then
    echo "==> OK: loveapp is running at commit $(git rev-parse --short HEAD)"
else
    echo "==> FAILED: check 'sudo journalctl -u loveapp -n 50'" >&2
    exit 1
fi