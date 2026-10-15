"""Settings for tests/unit and tests/integration: SQLite, in-memory cache and mail, eager Celery, fast hashing,
no telemetry. Nothing here needs docker, Postgres, Redis or RabbitMQ."""
import os
import tempfile

# the code base reads these with os.getenv at import time
for key, value in {
    "SECRET_KEY": "test-secret-key",
    "SIGNING_KEY": "test-signing-key-that-is-long-enough-for-hs256",
    "SITE_NAME": "NextGen Bank",
    "ADMIN_URL": "supersecret/",
    "DOMAIN": "testserver",
    "EMAIL_HOST": "localhost",
    "EMAIL_PORT": "25",
    "DEFAULT_FROM_EMAIL": "no-reply@test.local",
    "ADMIN_EMAIL": "admin@test.local",
    "BANK_NAME": "NextGen Bank",
    "BANK_CODE": "100",
    "BANK_BRANCH_CODE": "01",
    "CURRENCY_CODE_USD": "1",
    "CURRENCY_CODE_GBP": "2",
    "CURRENCY_CODE_KES": "3",
    "BANK_CARD_PREFIX": "4",
    "BANK_CARD_CODE": "1234",
    "CVV_SECRET_KEY": "test-cvv-secret",
    "LARGE_TRANSACTION_THRESHOLD": "10000",
    "FREQUENT_TRANSACTION_THRESHOLD": "10",
    "TIME_WINDOW_HOURS": "24",
    "COOKIE_SECURE": "False",
    "OTEL_SDK_DISABLED": "true",
    "THROTTLE_ANON_RATE": "100000/minute",
    "THROTTLE_USER_RATE": "100000/minute",
    "REDIS_URL": "",
    "CLOUDINARY_CLOUD_NAME": "",
    "CLOUDINARY_API_KEY": "",
    "CLOUDINARY_API_SECRET": "",
}.items():
    os.environ.setdefault(key, value)

from .local import *  # noqa: E402,F401,F403

SECRET_KEY = "test-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["*"]
DOMAIN = "testserver"
SITE_NAME = "NextGen Bank"
ADMIN_URL = "supersecret/"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast: thousands of users are created in tests

MEDIA_ROOT = tempfile.mkdtemp(prefix="nextgen-test-media-")
MEDIA_PUBLIC_URL = "http://testserver"
CLOUDINARY_ENABLED = False

LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = timedelta(minutes=1)  # noqa: F405
OTP_EXPIRATION = timedelta(minutes=5)    # noqa: F405
