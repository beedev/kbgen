#!/usr/bin/env bash
# First-boot entrypoint for the kbgen-bundled GLPI.
# Idempotent: the `.kbgen-installed` sentinel keeps subsequent boots fast.
set -eu

GLPI_HOME=/var/www/html/glpi
SENTINEL="$GLPI_HOME/.kbgen-installed"

wait_for_mariadb() {
  echo "[kbgen-glpi] waiting for MariaDB at ${GLPI_DB_HOST}:${GLPI_DB_PORT}..."
  for _ in $(seq 1 60); do
    if php -r "exit(@fsockopen('${GLPI_DB_HOST}', ${GLPI_DB_PORT}) ? 0 : 1);"; then
      return 0
    fi
    sleep 2
  done
  echo "[kbgen-glpi] ERROR: MariaDB did not become reachable in time" >&2
  return 1
}

wait_for_glpi_console() {
  echo "[kbgen-glpi] waiting for GLPI files under ${GLPI_HOME}..."
  for _ in $(seq 1 120); do
    if [ -f "${GLPI_HOME}/bin/console" ]; then
      return 0
    fi
    sleep 2
  done
  echo "[kbgen-glpi] ERROR: ${GLPI_HOME}/bin/console not found after bootstrap wait" >&2
  return 1
}

if [ -f "$SENTINEL" ]; then
  echo "[kbgen-glpi] already installed — starting upstream runtime"
  exec /opt/glpi-start.sh
fi

# Launch upstream bootstrap/runtime (downloads GLPI if needed, configures apache),
# then complete kbgen-specific DB/API setup once console and DB are available.
/opt/glpi-start.sh &
GLPI_PID=$!

wait_for_glpi_console
wait_for_mariadb

echo "[kbgen-glpi] running db:install"
cd "$GLPI_HOME"
if [ -f "${GLPI_HOME}/config/config_db.php" ]; then
  echo "[kbgen-glpi] db already configured — skipping db:install"
else
  php bin/console db:install \
    --no-interaction \
    --db-host="$GLPI_DB_HOST" --db-port="$GLPI_DB_PORT" \
    --db-name="$GLPI_DB_NAME" --db-user="$GLPI_DB_USER" --db-password="$GLPI_DB_PASSWORD" \
    --default-language=en_US
fi

echo "[kbgen-glpi] enabling REST API + opening localhost client for docker network"
php <<'PHP'
<?php
$dsn = sprintf(
    "mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4",
    getenv("GLPI_DB_HOST"),
    getenv("GLPI_DB_PORT"),
    getenv("GLPI_DB_NAME")
);
$pdo = new PDO($dsn, getenv("GLPI_DB_USER"), getenv("GLPI_DB_PASSWORD"), [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
]);
$pdo->exec("UPDATE glpi_configs SET value='1' WHERE `name` IN ('enable_api','enable_api_login_credentials','enable_api_login_external_token')");
$pdo->exec("UPDATE glpi_apiclients SET ipv4_range_start=0, ipv4_range_end=4294967295, app_token=NULL, is_active=1 WHERE id=1");
PHP

# Ensure runtime can write logs/config/session files after root-run install steps.
chown -R www-data:www-data "$GLPI_HOME"

touch "$SENTINEL"
echo "[kbgen-glpi] install complete — handing off to upstream runtime"
wait "$GLPI_PID"
