import random
import time
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

# ---- defaults ---------------------------------------------------------------
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

# ---- users ------------------------------------------------------------------
SEED_PASSWORD = "seedpass123"
EMAIL_DOMAIN = "example.com"
INACTIVE_USER_RATIO = 0.1
STAFF_USER_RATIO = 0.05

# ---- posts ------------------------------------------------------------------
PUBLISHED_RATIO = 0.7
NO_CATEGORY_RATIO = 0.1
MIN_TAGS_PER_POST = 0
MAX_TAGS_PER_POST = 5
TITLE_WORDS = 6
MIN_PARAGRAPHS = 3
MAX_PARAGRAPHS = 6
SLUG_MAX_LENGTH = Post._meta.get_field("slug").max_length
SLUG_SUFFIX_RESERVE = 6  # room for "-12345"
FIRST_DUPLICATE_SUFFIX = 2

# ---- comments ---------------------------------------------------------------
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

# ---- dates ------------------------------------------------------------------
DATE_RANGE_DAYS = 365
EDITED_POSTS_RATIO = 0.3
MIN_EDIT_DELAY_DAYS = 1
MAX_EDIT_DELAY_DAYS = 30

# ---- names ------------------------------------------------------------------
CATEGORY_NAMES = [
    "Python",
    "Django",
    "DevOps",
    "Databases",
    "Frontend",
    "Machine Learning",
    "Security",
    "Career",
]
TAG_NAMES = [
    "python",
    "django",
    "drf",
    "postgresql",
    "redis",
    "docker",
    "kubernetes",
    "linux",
    "git",
    "testing",
    "api",
    "rest",
    "jwt",
    "celery",
    "async",
    "performance",
    "security",
    "javascript",
    "react",
    "tutorial",
]

BATCH_SIZE = 500
SUMMARY_LABEL_WIDTH = 11
SUMMARY_NUMBER_WIDTH = 5


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        for name, value in (
            ("--users", users_count),
            ("--posts", posts_count),
            ("--comments", comments_count),
        ):
            if value < 0:
                raise CommandError(f"{name} must be 0 or greater, got {value}.")

        self.fake = Faker()
        started = time.perf_counter()

        with transaction.atomic():
            if clear:
                self._clear()

            users_created = self._create_users(users_count)
            categories_created = self._create_categories()
            tags_created = self._create_tags()
            posts = self._create_posts(posts_count)
            posts_created = len(posts)
            comments_created = self._create_comments(comments_count, posts)

        elapsed = time.perf_counter() - started

        if clear:
            self.stdout.write(self.style.WARNING("Existing data cleared."))

        for label, count in (
            ("Users", users_created),
            ("Categories", categories_created),
            ("Tags", tags_created),
            ("Posts", posts_created),
            ("Comments", comments_created),
        ):
            self.stdout.write(
                f"{label + ':':<{SUMMARY_LABEL_WIDTH}}"
                f"{count:>{SUMMARY_NUMBER_WIDTH}} created"
            )
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))

    # ------------------------------------------------------------------ #
    def _clear(self) -> None:
        """Delete everything except superusers."""
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _create_users(self, count: int) -> int:
        if not count:
            return 0

        used_emails = set(User.objects.values_list("email", flat=True))
        password = make_password(SEED_PASSWORD)  # hash once, reuse for all
        users = []

        for _ in range(count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            local_part = slugify(f"{first_name}.{last_name}").replace("-", ".")
            email = f"{local_part}@{EMAIL_DOMAIN}"
            suffix = FIRST_DUPLICATE_SUFFIX
            while email in used_emails:
                email = f"{local_part}{suffix}@{EMAIL_DOMAIN}"
                suffix += 1
            used_emails.add(email)

            users.append(
                User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=random.random() >= INACTIVE_USER_RATIO,
                    is_staff=random.random() < STAFF_USER_RATIO,
                )
            )

        User.objects.bulk_create(users, batch_size=BATCH_SIZE)
        return len(users)

    def _create_named(self, model: type[Category | Tag], names: list[str]) -> int:
        """Create Category/Tag rows from a list of names, skipping existing ones."""
        existing = set(model.objects.values_list("slug", flat=True))
        new_objects = [
            model(name=name, slug=slugify(name))
            for name in names
            if slugify(name) not in existing
        ]
        model.objects.bulk_create(new_objects)
        return len(new_objects)

    def _create_categories(self) -> int:
        return self._create_named(Category, CATEGORY_NAMES)

    def _create_tags(self) -> int:
        return self._create_named(Tag, TAG_NAMES)

    def _unique_slug(self, title: str, used_slugs: set[str]) -> str:
        base = slugify(title)[: SLUG_MAX_LENGTH - SLUG_SUFFIX_RESERVE].strip("-")
        slug = base
        suffix = FIRST_DUPLICATE_SUFFIX
        while slug in used_slugs:
            slug = f"{base}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        return slug

    def _random_datetime_between(self, start: datetime, end: datetime) -> datetime:
        """Return a random moment from start to end."""
        seconds = max(int((end - start).total_seconds()), 0)
        return start + timedelta(seconds=random.randint(0, seconds))

    def _set_post_dates(self, posts: list[Post]) -> None:
        """Spread posts over the last year; about 30% of them are edited later."""
        now = timezone.now()
        year_ago = now - timedelta(days=DATE_RANGE_DAYS)

        for post in posts:
            post.created_at = self._random_datetime_between(year_ago, now)
            if random.random() < EDITED_POSTS_RATIO:
                delay = timedelta(
                    days=random.randint(MIN_EDIT_DELAY_DAYS, MAX_EDIT_DELAY_DAYS)
                )
                post.updated_at = min(post.created_at + delay, now)
            else:
                post.updated_at = post.created_at

        Post.objects.bulk_update(
            posts, ["created_at", "updated_at"], batch_size=BATCH_SIZE
        )

    def _create_posts(self, count: int) -> list[Post]:
        if not count:
            return []

        author_ids = list(User.objects.values_list("id", flat=True))
        if not author_ids:
            raise CommandError(
                "Cannot create posts: there are no users. Use --users N."
            )

        category_ids = list(Category.objects.values_list("id", flat=True))
        tags = list(Tag.objects.all())
        used_slugs = set(Post.objects.values_list("slug", flat=True))
        posts = []

        for _ in range(count):
            title = self.fake.sentence(nb_words=TITLE_WORDS).rstrip(".")
            paragraphs = self.fake.paragraphs(
                nb=random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS)
            )
            has_category = category_ids and random.random() >= NO_CATEGORY_RATIO
            is_published = random.random() < PUBLISHED_RATIO

            posts.append(
                Post(
                    author_id=random.choice(author_ids),
                    title=title,
                    slug=self._unique_slug(title, used_slugs),
                    body="\n\n".join(paragraphs),
                    category_id=random.choice(category_ids) if has_category else None,
                    status=(
                        Post.Status.PUBLISHED if is_published else Post.Status.DRAFT
                    ),
                )
            )

        created = Post.objects.bulk_create(posts, batch_size=BATCH_SIZE)

        # After bulk_create the objects have ids, so tags can be attached.
        max_tags = min(MAX_TAGS_PER_POST, len(tags))
        for post in created:
            post.tags.set(
                random.sample(tags, random.randint(MIN_TAGS_PER_POST, max_tags))
            )

        self._set_post_dates(created)
        return created

    def _create_comments(self, count: int, new_posts: list[Post]) -> int:
        """Create comments on published posts only."""
        if not count:
            return 0

        author_ids = list(User.objects.values_list("id", flat=True))
        if not author_ids:
            raise CommandError(
                "Cannot create comments: there are no users. Use --users N."
            )

        published_posts = [
            post for post in new_posts if post.status == Post.Status.PUBLISHED
        ]
        if not published_posts:
            published_posts = list(
                Post.objects.filter(status=Post.Status.PUBLISHED).only(
                    "id", "created_at"
                )
            )

        if not published_posts:
            raise CommandError(
                "Cannot create comments: there are no published posts. Use --posts N."
            )

        comments = [
            Comment(
                post=random.choice(published_posts),
                author_id=random.choice(author_ids),
                body=" ".join(
                    self.fake.sentences(
                        nb=random.randint(MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES)
                    )
                ),
            )
            for _ in range(count)
        ]
        Comment.objects.bulk_create(comments, batch_size=BATCH_SIZE)

        now = timezone.now()
        for comment in comments:
            comment.created_at = self._random_datetime_between(
                comment.post.created_at, now
            )
        Comment.objects.bulk_update(comments, ["created_at"], batch_size=BATCH_SIZE)
        return len(comments)
