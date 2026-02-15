#!/usr/bin/env bash
set -euo pipefail

# Load DOMAIN and CERTBOT_EMAIL from .env file
if [ -f .env ]; then
    DOMAIN="${DOMAIN:-$(grep -E '^DOMAIN=' .env | cut -d '=' -f2-)}"
    CERTBOT_EMAIL="${CERTBOT_EMAIL:-$(grep -E '^CERTBOT_EMAIL=' .env | cut -d '=' -f2-)}"
fi

if [ -z "${DOMAIN:-}" ]; then
    echo "ERROR: DOMAIN is not set. Add DOMAIN=yourdomain.com to .env"
    exit 1
fi

if [ -z "${CERTBOT_EMAIL:-}" ]; then
    echo "ERROR: CERTBOT_EMAIL is not set. Add CERTBOT_EMAIL=you@example.com to .env"
    exit 1
fi

# Derive compose project name for volume references
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$(pwd)")}"

echo "Obtaining SSL certificate for ${DOMAIN}..."

# Run certbot in standalone mode (binds to port 80 directly)
# Nginx must NOT be running on port 80 when this runs
docker run --rm \
    -v "${COMPOSE_PROJECT_NAME}_certbot-certs:/etc/letsencrypt" \
    -v "${COMPOSE_PROJECT_NAME}_certbot-webroot:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$CERTBOT_EMAIL" \
    -d "$DOMAIN"

echo "Certificate obtained. Start services with: make prod-up"
