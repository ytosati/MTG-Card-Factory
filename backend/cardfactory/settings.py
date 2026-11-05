"""Django settings for Card Factory.
Details: specs/plan.md, sections 7 and 8.
"""

from core.environment import debug_enabled
from core.paths import data_dir

# Development placeholder only (see specs/plan.md, section 8).
SECRET_KEY = "dev-placeholder-not-secret"

DEBUG = debug_enabled()

# The server listens only on the local machine (see spec RN-29).
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

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
