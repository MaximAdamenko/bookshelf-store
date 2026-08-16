#!/bin/sh
set -e

live="/etc/letsencrypt/live/${DOMAIN}"

# nginx refuses to start without a certificate, but certbot's HTTP-01 challenge
# needs nginx already serving :80. Break the deadlock with a placeholder that
# the first real issue overwrites.
if [ ! -f "${live}/fullchain.pem" ]; then
    mkdir -p "${live}"
    openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
        -keyout "${live}/privkey.pem" \
        -out "${live}/fullchain.pem" \
        -subj "/CN=${DOMAIN}" 2>/dev/null
    echo "tls-bootstrap: placeholder certificate written for ${DOMAIN}"
fi

# Renewal writes new files but cannot signal this container, so pick them up here.
( while :; do sleep 6h; nginx -s reload 2>/dev/null || true; done ) &
