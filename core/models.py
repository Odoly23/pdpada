from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Append-only record of logins, ticket cancellations/refunds and other sensitive actions."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=60, db_index=True)
    detail = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.action}"

    @classmethod
    def record(cls, action, user=None, detail="", request=None, username=""):
        ip = None
        if request is not None:
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
        return cls.objects.create(
            user=user if getattr(user, "pk", None) else None,
            username=username or getattr(user, "username", ""),
            action=action,
            detail=detail,
            ip=ip or None,
        )
