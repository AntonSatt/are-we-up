#!/usr/bin/env bash
set -euo pipefail

# are-we-up remote agent setup
# Starts Node Exporter via Docker to expose system metrics.
# Does NOT modify your firewall or install anything.
#
# Usage:
#   bash setup.sh

echo "==> are-we-up remote agent setup"
echo ""

# --- Check Docker ---
if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not installed."
  echo ""
  echo "Install it first:"
  echo "  https://docs.docker.com/engine/install/ubuntu/"
  exit 1
fi

# --- Check if port 9100 is already in use ---
if ss -tlnp 2>/dev/null | grep -q ':9100 '; then
  echo "Warning: port 9100 is already in use on this machine."
  echo ""
  ss -tlnp 2>/dev/null | grep ':9100 '
  echo ""
  read -rp "Continue anyway? (y/N) " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
  fi
fi

# --- Start Node Exporter ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Starting Node Exporter..."
docker compose up -d

# --- Get this server's IP ---
SERVER_IP="$(hostname -I | awk '{print $1}')"

echo ""
echo "==> Done! Node Exporter is running."
echo ""
echo "    What it does:"
echo "      - Collects system metrics (CPU, memory, disk, network)"
echo "      - Listens on port 9100"
echo "      - Does not affect other apps on this server"
echo ""
echo "    Next steps:"
echo ""
echo "    1. Allow your monitoring server through the firewall:"
echo ""
echo "       sudo ufw allow from <your-public-ip> to any port 9100 proto tcp"
echo ""
echo "    2. On your are-we-up server, add this server to agents.json:"
echo ""
echo "       {"
echo "         \"targets\": [\"${SERVER_IP}:9100\"],"
echo "         \"labels\": { \"name\": \"$(hostname)\" }"
echo "       }"
echo ""
echo "       Prometheus picks it up automatically — no restart needed."
