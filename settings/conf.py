from pathlib import Path
from decouple import Config, RepositoryEnv

ENV_FILE = Path(__file__).resolve().parent / ".env"
config = Config(RepositoryEnv(ENV_FILE))
BLOG_ENV_ID = config("BLOG_ENV_ID", default="local")
BLOG_SECRET_KEY = config("BLOG_SECRET_KEY")