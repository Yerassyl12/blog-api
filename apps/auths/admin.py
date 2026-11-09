from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from apps.auths.models import User

TAB = "tab"
ACTIVE = "active"
INACTIVE = "inactive"
STAFF = "staff"
REGULAR = "regular"


class BlogUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self) -> str:
        # The admin form bypasses UserManager, so normalize here as well.
        return User.objects.normalize_email(self.cleaned_data["email"]).lower()


class BlogUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


# Django registers Group with the plain admin — re-register it with Unfold.
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = BlogUserChangeForm
    add_form = BlogUserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ("email",)
    list_display = (
        "display_header",
        "display_active",
        "display_staff",
        "posts_count",
    )
    list_filter = (
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    )
    list_filter_submit = True
    search_fields = ("email", "first_name", "last_name")
    actions = ("activate_users", "deactivate_users")
    readonly_fields = ("last_login",)

    fieldsets = (
        (
            _("Personal info"),
            {
                "classes": [TAB],
                "fields": ("email", "password", "first_name", "last_name"),
            },
        ),
        (
            _("Permissions"),
            {
                "classes": [TAB],
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"classes": [TAB], "fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description=_("User"), header=True, ordering="email")
    def display_header(self, obj: User) -> list[str]:
        initials = f"{obj.first_name[:1]}{obj.last_name[:1]}"
        return [obj.get_full_name(), obj.email, initials]

    @display(
        description=_("Active"),
        ordering="is_active",
        label={ACTIVE: "success", INACTIVE: "danger"},
    )
    def display_active(self, obj: User) -> tuple[str, str]:
        if obj.is_active:
            return ACTIVE, _("Active")
        return INACTIVE, _("Inactive")

    @display(
        description=_("Staff"),
        ordering="is_staff",
        label={STAFF: "info", REGULAR: "default"},
    )
    def display_staff(self, obj: User) -> tuple[str, str]:
        if obj.is_staff:
            return STAFF, _("Staff")
        return REGULAR, _("User")

    @display(description=_("Posts"), ordering="_posts_count")
    def posts_count(self, obj: User) -> int:
        return obj._posts_count

    @action(description=_("Activate selected users"), icon="check_circle")
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            ngettext("%d user activated.", "%d users activated.", updated) % updated,
            messages.SUCCESS,
        )

    @action(description=_("Deactivate selected users"), icon="block")
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            ngettext("%d user deactivated.", "%d users deactivated.", updated)
            % updated,
            messages.SUCCESS,
        )
