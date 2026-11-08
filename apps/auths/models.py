from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

EMAIL_MAX_LENGTH = 254
NAME_MAX_LENGTH = 50
EMAIL_REQUIRED_ERROR = "Email is required"
SUPERUSER_IS_STAFF_ERROR = "Superuser must have is_staff=True"
SUPERUSER_IS_SUPERUSER_ERROR = "Superuser must have is_superuser=True"


class UserManager(BaseUserManager["User"]):
    """Manager for the email-based custom user model."""

    use_in_migrations = True

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        if not email:
            raise ValueError(EMAIL_REQUIRED_ERROR)
        email = self.normalize_email(email).lower()

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(SUPERUSER_IS_STAFF_ERROR)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(SUPERUSER_IS_SUPERUSER_ERROR)

        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user that logs in with email instead of username."""

    email = models.EmailField(max_length=EMAIL_MAX_LENGTH, unique=True)
    first_name = models.CharField(max_length=NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=NAME_MAX_LENGTH)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        return self.first_name
