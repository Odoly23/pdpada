from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Staff user. Access is driven by Django Groups plus per-user permissions set by an admin."""

    preferred_language = models.CharField(
        _("Lian"), max_length=5, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    operator = models.ForeignKey(
        "fleet.Operator",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
        verbose_name=_("Operadór"),
        help_text=_("Uza-na'in operadór nia haree de'it dadus operadór rasik nian."),
    )
    phone = models.CharField(_("Telefone"), max_length=30, blank=True)
