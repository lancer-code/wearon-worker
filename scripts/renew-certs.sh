#!/usr/bin/env bash
set -euo pipefail

# Renew certificates using webroot mode (Nginx must be running)
docker run --rm \
    -v wearon-worker_certbot-certs:/etc/letsencrypt \
    -v wearon-worker_certbot-webroot:/var/www/certbot \
    certbot/certbot renew --webroot -w /var/www/certbot --quiet

# Reload Nginx to pick up new certificate (no restart needed)
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "Certificate renewal complete."
