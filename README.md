# Blog API

Blog REST API built with Django.

## ERD

![ERD](docs/erd.png)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
```

Create `settings/.env`:

```
BLOG_ENV_ID=local
BLOG_SECRET_KEY=change-me

# prod only
BLOG_ALLOWED_HOSTS=example.com,www.example.com
BLOG_DB_NAME=blog
BLOG_DB_USER=blog
BLOG_DB_PASSWORD=secret
BLOG_DB_HOST=localhost
BLOG_DB_PORT=5432
```

Run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Lint:

```bash
ruff check .
ruff format .
```
