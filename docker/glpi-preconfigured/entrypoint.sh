#!/usr/bin/env bash
# First-boot entrypoint for the kbgen-bundled GLPI.
# Idempotent: the `.kbgen-installed` sentinel keeps subsequent boots fast.
set -eu

GLPI_HOME=/var/www/html/glpi
SENTINEL="$GLPI_HOME/.kbgen-installed"

start_apache() {
  # The diouxx/glpi base image runs apache2-foreground as its CMD; we call it
  # directly here so our entrypoint replaces the original without losing the
  # supervised Apache process.
  exec apache2-foreground
}

if [ -f "$SENTINEL" ]; then
  echo "[kbgen-glpi] already installed — starting Apache"
  start_apache
fi

echo "[kbgen-glpi] waiting for MariaDB at ${GLPI_DB_HOST}:${GLPI_DB_PORT}…"
for _ in $(seq 1 60); do
  if php -r "exit(@fsockopen('${GLPI_DB_HOST}', ${GLPI_DB_PORT}) ? 0 : 1);"; then
    break
  fi
  sleep 2
done

echo "[kbgen-glpi] running db:install"
cd "$GLPI_HOME"
php bin/console db:install \
  --allow-superuser --no-interaction \
  --db-host="$GLPI_DB_HOST" --db-port="$GLPI_DB_PORT" \
  --db-name="$GLPI_DB_NAME" --db-user="$GLPI_DB_USER" --db-password="$GLPI_DB_PASSWORD" \
  --default-language=en_US

echo "[kbgen-glpi] enabling REST API + opening localhost client for docker network"
MARIADB="mysql -h${GLPI_DB_HOST} -u${GLPI_DB_USER} -p${GLPI_DB_PASSWORD} ${GLPI_DB_NAME}"
$MARIADB <<'SQL'
UPDATE glpi_configs SET value='1' WHERE name IN ('enable_api','enable_api_login_credentials','enable_api_login_external_token');
-- Open the built-in "full access from localhost" client to any IP; null the
-- app_token so kbgen can talk to GLPI with basic auth alone.
UPDATE glpi_apiclients SET ipv4_range_start=0, ipv4_range_end=4294967295, app_token=NULL, is_active=1 WHERE id=1;
SQL

touch "$SENTINEL"
echo "[kbgen-glpi] install complete — starting Apache"
start_apache
