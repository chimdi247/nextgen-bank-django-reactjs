FROM docker.io/alpine:3.20

# postgresql-client: pg_isready for the healthcheck
RUN apk add --no-cache pgbouncer postgresql-client bash \
    && mkdir -p /etc/pgbouncer /var/run/pgbouncer \
    && chown -R pgbouncer /etc/pgbouncer /var/run/pgbouncer

COPY ./docker/local/pgbouncer/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER pgbouncer
EXPOSE 6432
ENTRYPOINT ["/entrypoint.sh"]
