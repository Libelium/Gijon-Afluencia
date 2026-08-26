#!/bin/sh
# Development entrypoint: start-dev, theme caching disabled so template/CSS edits show on reload.
if [ -z "${BACKEND_URL}" ]; then
  echo "ERROR: BACKEND_URL environment variable is not defined. Stopping container."
  exit 1
fi

sed -i "s|__BACKEND_URL__|${BACKEND_URL}|g" /opt/keycloak/themes/pidtheme/login/theme.properties

exec /opt/keycloak/bin/kc.sh start-dev \
  --spi-theme-static-max-age=-1 \
  --spi-theme-cache-themes=false \
  --spi-theme-cache-templates=false
