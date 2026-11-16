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

Run (on an empty database this gives a working admin full of data):

```bash
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/admin/

## Seeding

`python manage.py seed` fills **all** models with fake data (Faker):
users, categories, tags, posts and comments.

| Argument     | Default | Description                                         |
|--------------|---------|-----------------------------------------------------|
| `--users`    | `20`    | Number of users to create                           |
| `--posts`    | `100`   | Number of posts to create                           |
| `--comments` | `500`   | Number of comments to create                        |
| `--clear`    | off     | Delete existing data (except superusers) first      |

- All seeded users share the password `seedpass123`.
- ~10% of users are inactive, ~5% are staff.
- 8 categories and 20 tags with real names; existing ones are skipped.
- ~70% of posts are published, ~30% drafts; ~10% have no category; 0–5 tags each.
- Comments are added only to published posts.
- Posts get a random `created_at` in the last 365 days; ~30% of them have
  `updated_at` 1–30 days later, the rest have `updated_at == created_at`.
- Every comment is created between its post's `created_at` and now.
- Safe to run several times in a row.

Example:

```bash
$ python manage.py seed --users 50 --posts 300 --comments 1500
Users:        50 created
Categories:    8 created
Tags:         20 created
Posts:       300 created
Comments:   1500 created
Done in 2.41 seconds

$ python manage.py seed --clear      # start over
```

## Queries

50 Django ORM queries live in `apps/blog/queries.py` (one function per query,
the `QUERIES` dict maps a number to a function). The `queries` command runs them
and shows how many SQL queries each one made.

```bash
python manage.py queries                    # all queries except 40–44 (they change data)
python manage.py queries --number 31        # only query 31 (works for 40–44 too)
python manage.py queries --number 6 --sql   # also print the SQL
```

Example:

```
$ python manage.py queries --number 31
#31 categories_with_post_count — 1 SQL query
  Django {'post_count': 27}
  Python {'post_count': 26}
  Databases {'post_count': 24}
  Security {'post_count': 23}
  DevOps {'post_count': 22}
  (8 rows)

$ python manage.py queries --number 6 --sql
#6 has_drafts — 1 SQL query
SELECT 1 AS "a" FROM "blog_post" WHERE "blog_post"."status" = 'draft' LIMIT 1
  True
```

Queries 40–44 change the data. Run `python manage.py seed --clear` to get fresh data.

## Admin

The admin uses [Django Unfold](https://unfoldadmin.com/):

- custom sidebar (Overview / Content / Users & Access — the last one for superusers only),
  drafts badge, `Cmd+K` / `Ctrl+K` search, environment badge, teal palette;
- dashboard with cards, posts-per-category chart, top authors and published/draft progress;
- posts: tabs All / Published / Drafts, dropdown & autocomplete filters, expandable rows
  with comments, row / bulk / list / detail / submit-line actions, WYSIWYG editor,
  tabbed edit form with paginated comments inline;
- users: header column with initials, colored labels, radio filters, tabbed form,
  activate / deactivate actions.

Set `BLOG_SQL_LOG=True` in `settings/.env` to log every SQL query (N+1 check).

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Post list with filters
![Post list](docs/screenshots/post-list.png)

### Post edit page
![Post edit](docs/screenshots/post-edit.png)

### User list
![User list](docs/screenshots/user-list.png)

Lint:

```bash
ruff check .
ruff format .
```
