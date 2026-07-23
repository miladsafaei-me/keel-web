import uuid

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0001_initial"),
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(blank=True, max_length=150, verbose_name="first name"),
                ),
                (
                    "last_name",
                    models.CharField(blank=True, max_length=150, verbose_name="last name"),
                ),
                (
                    "email",
                    models.EmailField(blank=True, max_length=254, verbose_name="email address"),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("slug", models.SlugField(blank=True, max_length=150, unique=True)),
                ("bio", models.TextField(blank=True)),
                ("avatar_url", models.URLField(blank=True, max_length=500)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="")),
                ("avatar_preset", models.CharField(blank=True, max_length=32)),
                ("avatar_config", models.JSONField(blank=True, default=dict)),
                ("country", models.CharField(blank=True, max_length=2)),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid phone number (digits, spaces, +, -, parentheses).",
                                regex=r"^\+?[0-9\s\-().]{6,32}$",
                            )
                        ],
                    ),
                ),
                (
                    "telegram_id",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid Telegram username (5-32 chars, letters/numbers/underscores, optional leading @).",
                                regex=r"^@?[A-Za-z][A-Za-z0-9_]{4,31}$",
                            )
                        ],
                    ),
                ),
                (
                    "whatsapp_phone",
                    models.CharField(
                        blank=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid phone number (digits, spaces, +, -, parentheses).",
                                regex=r"^\+?[0-9\s\-().]{6,32}$",
                            )
                        ],
                    ),
                ),
                (
                    "viber_phone",
                    models.CharField(
                        blank=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid phone number (digits, spaces, +, -, parentheses).",
                                regex=r"^\+?[0-9\s\-().]{6,32}$",
                            )
                        ],
                    ),
                ),
                ("social_links", models.JSONField(blank=True, default=dict)),
                ("role", models.CharField(blank=True, max_length=100)),
                ("current_session_key", models.CharField(blank=True, default="", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "db_table": "keel_web_auth_user",
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "abstract": False,
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
