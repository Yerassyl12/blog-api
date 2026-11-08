from pathlib import Path

from decouple import Config, Csv, RepositoryEnv

ENV_FILE = Path(__file__).resolve().parent / ".env"
DEFAULT_ENV_ID = "local"

config = Config(RepositoryEnv(ENV_FILE))

BLOG_ENV_ID = config("BLOG_ENV_ID", default=DEFAULT_ENV_ID)
BLOG_SECRET_KEY = config("BLOG_SECRET_KEY")
BLOG_ALLOWED_HOSTS = config("BLOG_ALLOWED_HOSTS", default="", cast=Csv())
