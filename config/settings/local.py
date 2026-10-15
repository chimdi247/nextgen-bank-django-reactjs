from os import getenv, path
from dotenv import load_dotenv
from .base import *  # noqa
from .base import BASE_DIR, env_bool, env_int


local_env_file = path.join(BASE_DIR, ".envs", ".env.local")

if path.isfile(local_env_file):
    load_dotenv(local_env_file)

SECRET_KEY = getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", False)

SITE_NAME = getenv("SITE_NAME")

ALLOWED_HOSTS = getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,api,nginx").split(",")

ADMIN_URL = getenv("ADMIN_URL")

EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = getenv("EMAIL_HOST")
EMAIL_PORT = getenv("EMAIL_PORT")
DEFAULT_FROM_EMAIL = getenv("DEFAULT_FROM_EMAIL")
DOMAIN = getenv("DOMAIN")
ADMIN_EMAIL = getenv("ADMIN_EMAIL")

MAX_UPLOAD_SIZE = 1 * 1024 * 1024

CSRF_TRUSTED_ORIGINS = getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:8080").split(",")

LOCKOUT_DURATION = timedelta(minutes=env_int("LOCKOUT_MINUTES", 1))

LOGIN_ATTEMPTS = env_int("LOGIN_ATTEMPTS", 5)

# 1 minute was too short when the OTP e-mail goes through RabbitMQ -> Celery -> SMTP
OTP_EXPIRATION = timedelta(minutes=env_int("OTP_EXPIRATION_MINUTES", 5))

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
