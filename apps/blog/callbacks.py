"""Callbacks used by the ``UNFOLD`` settings dict (see settings/base.py)."""

import json
from typing import Any

from django.db.models import Count, Q
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post
from settings.conf import BLOG_ENV_ID

ENV_PROD = "prod"
ENV_LABEL_LOCAL = (_("Local"), "warning")  # orange
ENV_LABEL_PROD = (_("Production"), "danger")  # red

TOP_AUTHORS_LIMIT = 5
PERCENT = 100


def environment_callback(request: HttpRequest) -> tuple[str, str]:
    """Badge in the header: "Local" (orange) or "Production" (red)."""
    if BLOG_ENV_ID == ENV_PROD:
        return ENV_LABEL_PROD
    return ENV_LABEL_LOCAL


def is_superuser(request: HttpRequest) -> bool:
    return request.user.is_superuser


def drafts_badge(request: HttpRequest) -> str | None:
    """Badge next to "Posts" in the sidebar: number of drafts."""
    drafts = Post.objects.filter(status=Post.Status.DRAFT).count()
    if not drafts:
        return None
    return str(drafts)


def _percent(part: int, total: int) -> int:
    if not total:
        return 0
    return round(part * PERCENT / total)


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict:
    """Data for templates/admin/index.html."""
    post_stats = Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
    )
    total_posts = post_stats["total"]

    categories = Category.objects.annotate(posts_count=Count("posts")).order_by(
        "-posts_count", "name"
    )
    chart = {
        "labels": [category.name for category in categories],
        "datasets": [
            {
                "label": str(_("Posts")),
                "data": [category.posts_count for category in categories],
            }
        ],
    }

    top_authors = (
        User.objects.annotate(posts_count=Count("posts"))
        .filter(posts_count__gt=0)
        .order_by("-posts_count", "email")[:TOP_AUTHORS_LIMIT]
    )

    context.update(
        {
            "cards": [
                {
                    "title": _("Users"),
                    "value": User.objects.count(),
                    "icon": "person",
                },
                {
                    "title": _("Published posts"),
                    "value": post_stats["published"],
                    "icon": "check_circle",
                },
                {
                    "title": _("Drafts"),
                    "value": post_stats["drafts"],
                    "icon": "edit_note",
                },
                {
                    "title": _("Comments"),
                    "value": Comment.objects.count(),
                    "icon": "chat",
                },
            ],
            "posts_per_category_chart": json.dumps(chart),
            "top_authors_table": {
                "headers": [_("Author"), _("Email"), _("Posts")],
                "rows": [
                    [author.get_full_name(), author.email, author.posts_count]
                    for author in top_authors
                ],
            },
            "progress": [
                {
                    "title": _("Published"),
                    "description": post_stats["published"],
                    "value": _percent(post_stats["published"], total_posts),
                },
                {
                    "title": _("Drafts"),
                    "description": post_stats["drafts"],
                    "value": _percent(post_stats["drafts"], total_posts),
                },
            ],
        }
    )
    return context
