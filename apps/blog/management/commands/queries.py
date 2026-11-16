from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Count, Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auths.models import User
from apps.blog.models import Post
from apps.blog.queries import QUERIES

ROWS_TO_SHOW = 5
INDENT = "  "
CHANGING_QUERIES = range(40, 45)

SAMPLE_PAGE = 2
SAMPLE_DAYS = 30
SAMPLE_MIN_POSTS = 5
SAMPLE_EMAIL_DOMAIN = "example.com"
SAMPLE_CATEGORY_SLUG = "python"
SAMPLE_CATEGORY_SLUGS = ["python", "django", "devops"]
SAMPLE_SOURCE_CATEGORY_SLUG = "career"
SAMPLE_TARGET_CATEGORY_SLUG = "django"
SAMPLE_TAG_SLUG = "python"
SAMPLE_CATEGORY_TAG_SLUG = "tutorial"
SAMPLE_TAG_NAME = "Django ORM"
SAMPLE_LAST_NAME_LENGTH = 3
MIN_TAGS_FOR_PAIR = 2


def sample_post_slug() -> str | None:
    return Post.objects.values_list("slug", flat=True).first()


def sample_title_word() -> str:
    title = Post.objects.values_list("title", flat=True).first() or ""
    return title.split()[0] if title else ""


def sample_author_email() -> str | None:
    return (
        User.objects.filter(posts__status=Post.Status.PUBLISHED)
        .values_list("email", flat=True)
        .first()
    )


def sample_tag_pair() -> list[str]:
    post = (
        Post.objects.annotate(tag_count=Count("tags"))
        .filter(tag_count__gte=MIN_TAGS_FOR_PAIR)
        .order_by("id")
        .first()
    )
    if post is None:
        return [SAMPLE_TAG_SLUG, SAMPLE_TAG_SLUG]
    return list(post.tags.order_by("slug").values_list("slug", flat=True))


def sample_full_name_part() -> str:
    user = User.objects.exclude(first_name="").order_by("id").first()
    if user is None:
        return ""
    return f"{user.first_name} {user.last_name[:SAMPLE_LAST_NAME_LENGTH]}".lower()


def current_year() -> int:
    return timezone.now().year


def current_month() -> int:
    return timezone.now().month


def month_ago() -> date:
    return timezone.now().date() - timedelta(days=SAMPLE_DAYS)


def today() -> date:
    return timezone.now().date()


QUERY_ARGUMENTS: dict[int, dict[str, Any]] = {
    4: {"slug": sample_post_slug},
    7: {"page": SAMPLE_PAGE},
    8: {"word": sample_title_word},
    9: {"domain": SAMPLE_EMAIL_DOMAIN},
    11: {"slugs": SAMPLE_CATEGORY_SLUGS},
    12: {"year": current_year, "month": current_month},
    13: {"days": SAMPLE_DAYS},
    14: {"start": month_ago, "end": today},
    15: {"email": sample_author_email},
    16: {"tag_slug": SAMPLE_TAG_SLUG},
    17: {"category_slug": SAMPLE_CATEGORY_SLUG},
    21: {
        "first_slug": lambda: sample_tag_pair()[0],
        "second_slug": lambda: sample_tag_pair()[1],
    },
    22: {"text": sample_title_word},
    34: {"min_posts": SAMPLE_MIN_POSTS},
    37: {"text": sample_full_name_part},
    40: {"name": SAMPLE_TAG_NAME},
    41: {"days": SAMPLE_DAYS},
    42: {"category_slug": SAMPLE_CATEGORY_SLUG, "tag_slug": SAMPLE_CATEGORY_TAG_SLUG},
    43: {
        "source_slug": SAMPLE_SOURCE_CATEGORY_SLUG,
        "target_slug": SAMPLE_TARGET_CATEGORY_SLUG,
    },
}


class Command(BaseCommand):
    help = "Run the ORM queries from apps/blog/queries.py."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only this query")
        parser.add_argument(
            "--sql", action="store_true", help="Print the SQL sent to the database"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options["number"]
        show_sql: bool = options["sql"]

        if number is None:
            numbers = [n for n in QUERIES if n not in CHANGING_QUERIES]
        elif number in QUERIES:
            numbers = [number]
        else:
            raise CommandError(f"Query #{number} does not exist. Use 1-{max(QUERIES)}.")

        for query_number in numbers:
            self._run(query_number, show_sql)

    def _run(self, number: int, show_sql: bool) -> None:
        function = QUERIES[number]
        arguments = {
            name: value() if callable(value) else value
            for name, value in QUERY_ARGUMENTS.get(number, {}).items()
        }

        annotations: list[str] = []
        with CaptureQueriesContext(connection) as context:
            result = function(**arguments)
            if isinstance(result, QuerySet):
                annotations = list(result.query.annotations)
                result = list(result)

        count = len(context.captured_queries)
        word = "query" if count == 1 else "queries"
        self.stdout.write(
            self.style.SUCCESS(f"#{number} {function.__name__} — {count} SQL {word}")
        )
        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(self.style.SQL_KEYWORD(captured["sql"]))

        if isinstance(result, dict):
            result = [f"{key}: {value}" for key, value in result.items()]

        if not isinstance(result, list):
            self.stdout.write(f"{INDENT}{self._format_row(result, annotations)}")
            return

        for row in result[:ROWS_TO_SHOW]:
            self.stdout.write(f"{INDENT}{self._format_row(row, annotations)}")
        self.stdout.write(f"{INDENT}({len(result)} rows)")

    def _format_row(self, row: Any, annotations: list[str]) -> str:
        if isinstance(row, Model) and annotations:
            values = {name: getattr(row, name) for name in annotations}
            return f"{row} {values}"
        return str(row)
