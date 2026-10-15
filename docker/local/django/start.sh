#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# The schema is created by docker/local/postgres/init/*.sql and its migration history is pre-recorded, so this only
# applies what the SQL does not cover (django_celery_beat) and emits post_migrate (content types / permissions).
python manage.py migrate --no-input
python manage.py collectstatic --no-input

# gunicorn (not runserver): several workers, each with its own OpenTelemetry exporters (config/gunicorn.conf.py)
exec gunicorn config.wsgi:application --config config/gunicorn.conf.py
