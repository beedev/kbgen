# Pre-configured GLPI image for the kbgen single-stack deploy.
#
# Wraps diouxx/glpi with an entrypoint that, on first container start:
#   1. Runs `php bin/console db:install` against the co-located MariaDB
#   2. Enables the REST API + default-localhost API client (no app_token)
#   3. Loosens the IP range so the kbgen container (on the compose network)
#      can hit it
#
# Subsequent boots are no-ops thanks to the sentinel at /var/www/html/glpi/.kbgen-installed.
FROM --platform=linux/amd64 diouxx/glpi:latest

# The base image sets up Apache; we inject our own entrypoint that runs the
# install routine before handing off to Apache.
COPY entrypoint.sh /usr/local/bin/kbgen-glpi-entrypoint.sh
RUN chmod +x /usr/local/bin/kbgen-glpi-entrypoint.sh

ENV GLPI_DB_HOST=glpi-db \
    GLPI_DB_PORT=3306 \
    GLPI_DB_NAME=glpidb \
    GLPI_DB_USER=glpi \
    GLPI_DB_PASSWORD=glpi_dev_2026 \
    VERSION_GLPI=10.0.24 \
    GLPI_ADMIN_USER=glpi \
    GLPI_ADMIN_PASSWORD=glpi

ENTRYPOINT ["/usr/local/bin/kbgen-glpi-entrypoint.sh"]
