#!/usr/bin/env bash
set -euo pipefail

# Load DOMAIN from .env file
if [ -f .env ]; then
    DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d '=' -f2-)
fi

if [ -z "${DOMAIN:-}" ]; then
    echo "ERROR: DOMAIN is not set. Add DOMAIN=yourdomain.com to .env"
    exit 1
fi

EMAIL="${CERTBOT_EMAIL:-}"
if [ -z "$EMAIL" ]; then
    echo "ERROR: CERTBOT_EMAIL is not set. Pass it as env var or add to .env"
    exit 1
fi

echo "Obtaining SSL certificate for ${DOMAIN}..."

# Run certbot in standalone mode (binds to port 80 directly)
# Nginx must NOT be running on port 80 when this runs
docker run --rm \
    -v wearon-worker_certbot-certs:/etc/letsencrypt \
    -v wearon-worker_certbot-webroot:/var/www/certbot \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN"

echo "Certificate obtained. Start services with: make prod-up"
