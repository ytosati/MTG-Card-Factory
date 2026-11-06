"""Django settings for Card Factory.
Details: specs/plan.md, sections 7 and 8.
"""

from core.app_log import logging_settings
from core.config import load_config
from core.environment import debug_enabled
from core.paths import data_dir, frontend_build_dir
from core.secret_key import get_secret_key

SECRET_KEY = get_secret_key()

DEBUG = debug_enabled()

# The server listens only on the local machine (see spec RN-29).
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Read once at startup: a changed APP_PORT applies at the next start (see spec RN-47).
# An invalid or empty value gives the default port and never blocks startup.
RUNNING_PORT = load_config().app_port

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "catalog",
    "providers",
    "validators",
    "generation",
    "cards",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cardfactory.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "cardfactory.wsgi.application"

# WAL, a busy timeout and IMMEDIATE transactions because job threads write
# while server threads read (see specs/plan.md, section 7 and docs/DECISIONS.md).
# init_command runs on every new connection.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(data_dir() / "cardfactory.sqlite3"),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL;",
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# The built frontend (see specs/plan.md, section 9.5): a Path or a str, read by
# the serving views on every request.
FRONTEND_BUILD_DIR = frontend_build_dir()

# Every handler redacts the API keys (see specs/plan.md, section 8).
LOGGING = logging_settings()

REST_FRAMEWORK = {
    # No accounts in the product: an Authorization header is never read.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "EXCEPTION_HANDLER": "api.exceptions.exception_handler",
    # JSON only: an API answer is never an HTML page.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
