from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from django.contrib import admin, messages
from django.db import models
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_PREVIEW_LENGTH = 60
COMMENTS_PER_PAGE = 10
TAB = "tab"
COMMENT_CHANGELIST = "admin:blog_comment_changelist"
POST_CHANGELIST = "admin:blog_post_changelist"
POST_FILTER_PARAM = "post__id__exact"
TAG_FILTER_PARAM = "tags__id__exact"


# --------------------------------------------------------------------------- #
# Expandable row sections
# --------------------------------------------------------------------------- #
class CategoryPostsSection(TableSection):
    verbose_name = _("Posts in this category")
    related_name = "posts"
    fields = ("title", "author", "status", "created_at")


class PostCommentsSection(TableSection):
    verbose_name = _("Comments")
    related_name = "comments"
    fields = ("author", "short_body", "created_at")

    def short_body(self, instance: Comment) -> str:
        return Truncator(instance.body).chars(COMMENT_PREVIEW_LENGTH)

    short_body.short_description = _("Body")


# --------------------------------------------------------------------------- #
# Category & Tag
# --------------------------------------------------------------------------- #
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_sections = [CategoryPostsSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        posts = Post.objects.select_related("author")
        return (
            super()
            .get_queryset(request)
            .annotate(_posts_count=Count("posts"))
            .prefetch_related(Prefetch("posts", queryset=posts))
        )

    @display(description=_("Posts"), ordering="_posts_count")
    def posts_count(self, obj: Category) -> int:
        return obj._posts_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description=_("Posts"), ordering="_posts_count")
    def posts_count(self, obj: Tag) -> int:
        return obj._posts_count


# --------------------------------------------------------------------------- #
# Comment
# --------------------------------------------------------------------------- #
@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post_title", "author", "short_body", "created_at")
    list_select_related = ("post", "author")
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")

    @display(description=_("Post"), ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description=_("Body"))
    def short_body(self, obj: Comment) -> str:
        return Truncator(obj.body).chars(COMMENT_PREVIEW_LENGTH)


# --------------------------------------------------------------------------- #
# Post
# --------------------------------------------------------------------------- #
class CommentInline(TabularInline):
    model = Comment
    extra = 0
    tab = True
    per_page = COMMENTS_PER_PAGE
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    verbose_name_plural = _("Comments")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Comment]:
        return super().get_queryset(request).select_related("author", "post")


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # ---- list page --------------------------------------------------------
    list_display = (
        "display_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count",
        "created_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("title", "body", "author__email")
    list_sections = [PostCommentsSection]

    # ---- actions ----------------------------------------------------------
    actions = ("publish_selected", "move_to_drafts")
    actions_row = ("toggle_status",)
    actions_list = ("publish_all_drafts",)
    actions_detail = ("open_comments",)
    actions_submit_line = ("save_and_publish",)

    # ---- edit page --------------------------------------------------------
    fieldsets = (
        (_("Content"), {"classes": [TAB], "fields": ("title", "slug", "body")}),
        (
            _("Classification"),
            {"classes": [TAB], "fields": ("category", "tags", "status")},
        ),
        (
            _("Meta"),
            {"classes": [TAB], "fields": ("author", "created_at", "updated_at")},
        ),
    )
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("created_at", "updated_at")
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    warn_unsaved_form = True
    inlines = (CommentInline,)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        comments = Comment.objects.select_related("author")
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related("tags", Prefetch("comments", queryset=comments))
            .annotate(_comments_count=Count("comments", distinct=True))
        )

    # ---- columns ----------------------------------------------------------
    @display(description=_("Post"), header=True, ordering="title")
    def display_header(self, obj: Post) -> list[str]:
        return [obj.title, obj.author.get_full_name() or obj.author.email]

    @display(
        description=_("Status"),
        ordering="status",
        label={
            Post.Status.PUBLISHED: "success",
            Post.Status.DRAFT: "warning",
        },
    )
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description=_("Tags"), dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict:
        # len(...all()) uses the prefetch; .count() would hit the DB per row.
        tags = obj.tags.all()
        changelist = reverse(POST_CHANGELIST)
        return {
            "title": ngettext("%d tag", "%d tags", len(tags)) % len(tags),
            "items": [
                {
                    "title": tag.name,
                    "link": f"{changelist}?{TAG_FILTER_PARAM}={tag.pk}",
                }
                for tag in tags
            ],
        }

    @display(description=_("Comments"), ordering="_comments_count")
    def comments_count(self, obj: Post) -> int:
        return obj._comments_count

    # ---- bulk actions (checkboxes) ----------------------------------------
    @action(description=_("Publish selected"), icon="publish")
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(
            request,
            ngettext("%d post published.", "%d posts published.", updated) % updated,
            messages.SUCCESS,
        )

    @action(description=_("Move to drafts"), icon="edit_note")
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = queryset.update(status=Post.Status.DRAFT)
        self.message_user(
            request,
            ngettext("%d post moved to drafts.", "%d posts moved to drafts.", updated)
            % updated,
            messages.SUCCESS,
        )

    # ---- row action -------------------------------------------------------
    @action(description=_("Publish / unpublish"), icon="sync_alt")
    def toggle_status(
        self, request: HttpRequest, object_id: int
    ) -> HttpResponseRedirect:
        post = get_object_or_404(Post, pk=object_id)
        if post.status == Post.Status.PUBLISHED:
            post.status = Post.Status.DRAFT
        else:
            post.status = Post.Status.PUBLISHED
        post.save(update_fields=["status", "updated_at"])
        self.message_user(
            request,
            _("“%(title)s” is now %(status)s.")
            % {"title": post.title, "status": post.get_status_display()},
            messages.SUCCESS,
        )
        return HttpResponseRedirect(
            request.headers.get("referer") or reverse(POST_CHANGELIST)
        )

    # ---- list action (above the table) ------------------------------------
    @action(description=_("Publish all drafts"), icon="done_all")
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponseRedirect:
        updated = Post.objects.filter(status=Post.Status.DRAFT).update(
            status=Post.Status.PUBLISHED
        )
        self.message_user(
            request,
            ngettext("%d draft published.", "%d drafts published.", updated) % updated,
            messages.SUCCESS,
        )
        return HttpResponseRedirect(reverse(POST_CHANGELIST))

    # ---- detail action (post page) ----------------------------------------
    @action(description=_("Open comments"), icon="chat")
    def open_comments(
        self, request: HttpRequest, object_id: int
    ) -> HttpResponseRedirect:
        url = reverse(COMMENT_CHANGELIST)
        return HttpResponseRedirect(f"{url}?{POST_FILTER_PARAM}={object_id}")

    # ---- submit line (next to "Save") -------------------------------------
    @action(description=_("Save & publish"))
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        # Runs after the object has been saved.
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=["status", "updated_at"])
