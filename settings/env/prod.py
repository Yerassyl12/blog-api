from ..base import *
from ..conf import config

DEBUG = False

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config("BLOG_DB_NAME"),
        'USER': config("BLOG_DB_USER"),
        'PASSWORD': config("BLOG_DB_PASSWORD"),
        'HOST': config("BLOG_DB_HOST"),
        'PORT': config("BLOG_DB_PORT"),
    }       
}
