#!/usr/bin/env bash
set -euo pipefail

cd /opt/wearon

echo "[$(date)] Starting certificate renewal check..."

# Derive compose project name for volume references
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$(pwd)")}"

# Renew certificates using webroot mode (Nginx must be running)
docker run --rm \
    -v "${COMPOSE_PROJECT_NAME}_certbot-certs:/etc/letsencrypt" \
    -v "${COMPOSE_PROJECT_NAME}_certbot-webroot:/var/www/certbot" \
    certbot/certbot renew --webroot -w /var/www/certbot --quiet

# Reload Nginx to pick up new certificate (no restart needed)
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload

echo "[$(date)] Certificate renewal check complete."
