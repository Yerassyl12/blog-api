from ..base import *  # noqa: F401,F403
from ..base import BASE_DIR, LOGGING
from ..conf import config

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Set BLOG_SQL_LOG=True in settings/.env to print every SQL query
# (useful for spotting N+1 problems in the admin).
if config("BLOG_SQL_LOG", default=False, cast=bool):
    LOGGING["loggers"] = {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    }
