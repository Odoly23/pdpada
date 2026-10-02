from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Rejistu asaun sensivel (la bele edita/hamoos husi aplikasaun)."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='audit_logs')
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=50, db_index=True)
    target = models.CharField(max_length=100, blank=True)
    detail = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.action} {self.target}'
