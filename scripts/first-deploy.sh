#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:?Usage: ./first-deploy.sh <domain>}"
DEPLOY_DIR="/opt/wearon"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== WearOn First Deploy ==="
echo "Domain: ${DOMAIN}"
echo "Source: ${SCRIPT_DIR}"
echo "Target: ${DEPLOY_DIR}"
echo ""

# 1. Check prerequisites
echo "[1/8] Checking prerequisites..."
for cmd in docker python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd is not installed. Install it first."
        exit 1
    fi
done

if ! docker compose version &>/dev/null; then
    echo "ERROR: Docker Compose plugin is not installed."
    exit 1
fi

echo "  Docker $(docker --version | grep -oP '\d+\.\d+\.\d+')"
echo "  Docker Compose $(docker compose version --short)"

# 2. Create directory structure
echo "[2/8] Creating ${DEPLOY_DIR}..."
if [ "$(id -u)" -eq 0 ]; then
    mkdir -p "${DEPLOY_DIR}"
else
    sudo mkdir -p "${DEPLOY_DIR}"
    sudo chown "$(id -u):$(id -g)" "${DEPLOY_DIR}"
fi

# 3. Copy config files
echo "[3/8] Copying configuration files..."
if [ "$(realpath "${SCRIPT_DIR}")" = "$(realpath "${DEPLOY_DIR}")" ]; then
    echo "  Source and target are identical, skipping copy."
else
    cp "${SCRIPT_DIR}/docker-compose.prod.yml" "${DEPLOY_DIR}/"
    cp -r "${SCRIPT_DIR}/nginx" "${DEPLOY_DIR}/"
    cp -r "${SCRIPT_DIR}/monitoring" "${DEPLOY_DIR}/"
    cp -r "${SCRIPT_DIR}/scripts" "${DEPLOY_DIR}/"
    cp "${SCRIPT_DIR}/.env.example" "${DEPLOY_DIR}/.env.example"
fi

# 4. Create .env from template
echo "[4/8] Setting up environment..."
if [ ! -f "${DEPLOY_DIR}/.env" ]; then
    sed "s/^DOMAIN=.*/DOMAIN=${DOMAIN}/" "${DEPLOY_DIR}/.env.example" > "${DEPLOY_DIR}/.env"
    echo ""
    echo "  Created ${DEPLOY_DIR}/.env from template."
    echo "  IMPORTANT: Edit ${DEPLOY_DIR}/.env and fill in all required values:"
    echo "    - REDIS_PASSWORD"
    echo "    - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY"
    echo "    - OPENAI_API_KEY"
    echo "    - CERTBOT_EMAIL"
    echo "    - GF_SECURITY_ADMIN_PASSWORD"
    echo "    - WHATSAPP_APP_TOKEN, WHATSAPP_RECIPIENT_NUMBER"
    echo ""
    read -rp "  Press Enter after editing .env to continue..."
else
    echo "  ${DEPLOY_DIR}/.env already exists, skipping."
fi

cd "${DEPLOY_DIR}"

# 5. Pull Docker images
echo "[5/8] Pulling Docker images..."
docker compose -f docker-compose.prod.yml pull

# 6. Obtain SSL certificate
echo "[6/8] Obtaining SSL certificate..."
bash scripts/init-ssl.sh

# 7. Start all services
echo "[7/8] Starting services..."
docker compose -f docker-compose.prod.yml up -d

# 8. Wait for health check
echo "[8/8] Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker compose -f docker-compose.prod.yml ps --format json 2>/dev/null | \
       python3 -c "import sys,json; lines=[json.loads(l) for l in sys.stdin]; sys.exit(0 if all(s.get('Health','')=='healthy' for s in lines if s.get('Health')) else 1)" 2>/dev/null; then
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo "  Waiting... (${ELAPSED}s/${MAX_WAIT}s)"
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "WARNING: Some services may not be healthy yet. Check with:"
    echo "  cd ${DEPLOY_DIR} && docker compose -f docker-compose.prod.yml ps"
else
    echo "  All services healthy!"
fi

# Install certificate renewal cron job (daily at 3 AM)
echo "Installing certificate renewal cron job..."
CRON_CMD="0 3 * * * /opt/wearon/scripts/renew-certs.sh >> /var/log/wearon-cert-renewal.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'renew-certs.sh'; echo "$CRON_CMD" ) | crontab -
echo "  Cron job installed: daily at 3:00 AM"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Service URLs:"
echo "  Health:  https://${DOMAIN}/health"
echo "  Grafana: https://${DOMAIN}/grafana/"
echo ""
echo "Useful commands:"
echo "  cd ${DEPLOY_DIR}"
echo "  docker compose -f docker-compose.prod.yml ps      # Service status"
echo "  docker compose -f docker-compose.prod.yml logs -f  # Follow logs"
