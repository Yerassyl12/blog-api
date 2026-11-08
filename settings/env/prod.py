from ..base import *  # noqa: F401,F403
from ..conf import BLOG_ALLOWED_HOSTS, config

DEBUG = False

ALLOWED_HOSTS = BLOG_ALLOWED_HOSTS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("BLOG_DB_NAME"),
        "USER": config("BLOG_DB_USER"),
        "PASSWORD": config("BLOG_DB_PASSWORD"),
        "HOST": config("BLOG_DB_HOST"),
        "PORT": config("BLOG_DB_PORT"),
    }
}
