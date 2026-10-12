import hashlib
import hmac
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class QuotaGroup(models.TextChoices):
    PASSENGER = "passenger", _("Pasajeiru")
    VEHICLE = "vehicle", _("Veíkulu")
    GOODS = "goods", _("Sasán / Animál")


class FareItem(models.Model):
    """Something that can be sold: a passenger category, a vehicle type, a cargo item or an animal.

    The catalog is managed by APORTIL admins. An item without a Fare on a route is not sold there.
    """

    name_tet = models.CharField("Tetun", max_length=100)
    name_pt = models.CharField("Português", max_length=100, blank=True)
    name_en = models.CharField("English", max_length=100, blank=True)
    name_id = models.CharField("Indonesia", max_length=100, blank=True)
    quota_group = models.CharField(max_length=10, choices=QuotaGroup.choices)
    age_min = models.PositiveSmallIntegerField(null=True, blank=True, help_text=_("Pasajeiru: idade minimu"))
    age_max = models.PositiveSmallIntegerField(null=True, blank=True, help_text=_("Pasajeiru: idade maximu"))
    foreigner_only = models.BooleanField(default=False)
    requires_plate = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["quota_group", "sort_order", "name_tet"]

    def __str__(self):
        return self.name_tet

    def display_name(self, lang=None):
        from django.utils import translation

        lang = (lang or translation.get_language() or "tet").split("-")[0]
        return getattr(self, f"name_{lang}", "") or self.name_tet


class Fare(models.Model):
    route = models.ForeignKey("fleet.Route", on_delete=models.CASCADE, related_name="fares")
    item = models.ForeignKey(FareItem, on_delete=models.CASCADE, related_name="fares")
    price = models.DecimalField(max_digits=8, decimal_places=2)  # USD

    class Meta:
        constraints = [models.UniqueConstraint(fields=["route", "item"], name="uniq_fare")]

    def __str__(self):
        return f"{self.route} / {self.item}: ${self.price}"


class Sailing(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Agendadu")
        DELAYED = "delayed", _("Atrazadu")
        CANCELLED = "cancelled", _("Kansela")
        DEPARTED = "departed", _("Partida ona")
        COMPLETED = "completed", _("Remata")

    vessel = models.ForeignKey("fleet.Vessel", on_delete=models.PROTECT, related_name="sailings")
    route = models.ForeignKey("fleet.Route", on_delete=models.PROTECT, related_name="sailings")
    departure = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    sales_close_minutes = models.PositiveSmallIntegerField(default=60)
    note = models.CharField(max_length=255, blank=True)
    replaced_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replaces")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["departure"]
        permissions = [("manage_schedule", "Can create and change sailings")]

    def __str__(self):
        return f"{self.vessel} {self.route} {timezone.localtime(self.departure):%d/%m/%Y %H:%M}"

    @property
    def sales_open(self):
        if self.status not in (self.Status.SCHEDULED, self.Status.DELAYED):
            return False
        return timezone.now() < self.departure - timedelta(minutes=self.sales_close_minutes)


class SailingQuota(models.Model):
    sailing = models.ForeignKey(Sailing, on_delete=models.CASCADE, related_name="quotas")
    quota_group = models.CharField(max_length=10, choices=QuotaGroup.choices)
    capacity = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sailing", "quota_group"], name="uniq_quota")]

    def __str__(self):
        return f"{self.sailing_id} {self.quota_group}: {self.capacity}"

    @property
    def sold(self):
        return (
            Ticket.objects.filter(sailing=self.sailing, item__quota_group=self.quota_group)
            .exclude(status__in=[Ticket.Status.CANCELLED, Ticket.Status.REFUNDED])
            .aggregate(n=models.Sum("quantity"))["n"]
            or 0
        )

    @property
    def remaining(self):
        return max(self.capacity - self.sold, 0)


class DocumentType(models.TextChoices):
    ELEITORAL = "eleitoral", _("Kartaun Eleitorál")
    BI = "bi", _("Bilhete Identidade (BI)")
    PASSPORT = "passport", _("Pasaporte")
    BAPTISM = "baptism", _("Sertifikadu Batismu")
    RDTL = "rdtl", _("Sertifikadu RDTL")
    OTHER = "other", _("Seluk")


def document_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"documents/{timezone.now():%Y/%m}/{secrets.token_hex(16)}.{ext}"


def proof_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"proofs/{timezone.now():%Y/%m}/{secrets.token_hex(16)}.{ext}"


class Ticket(models.Model):
    """One ticket per passenger / vehicle / cargo line, each paid for individually."""

    class Status(models.TextChoices):
        ISSUED = "issued", _("Emite ona")
        BOARDED = "boarded", _("Tama ona ro")
        CANCELLED = "cancelled", _("Kansela")
        REFUNDED = "refunded", _("Fila fali osan")

    class Payment(models.TextChoices):
        CASH = "cash", _("Osan kontante")
        TRANSFER = "transfer", _("Transferénsia banku")

    serial = models.CharField(max_length=20, unique=True, editable=False)
    sailing = models.ForeignKey(Sailing, on_delete=models.PROTECT, related_name="tickets")
    item = models.ForeignKey(FareItem, on_delete=models.PROTECT, related_name="tickets")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ISSUED, db_index=True)

    # Passenger data (passenger tickets only)
    full_name = models.CharField(max_length=150, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=1, blank=True, choices=[("M", "M"), ("F", "F")])
    nationality = models.CharField(max_length=60, blank=True)
    document_type = models.CharField(max_length=12, choices=DocumentType.choices, blank=True)
    document_number = models.CharField(max_length=60, blank=True)
    document_photo = models.ImageField(upload_to=document_upload_path, blank=True)
    document_deleted_at = models.DateTimeField(null=True, blank=True)
    plate_number = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_whatsapp = models.CharField(max_length=30, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    # Payment
    payment_method = models.CharField(max_length=10, choices=Payment.choices, default=Payment.CASH)
    transfer_reference = models.CharField(max_length=60, blank=True)
    transfer_proof = models.ImageField(upload_to=proof_upload_path, blank=True)

    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    boarded_at = models.DateTimeField(null=True, blank=True)
    boarded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("issue_ticket", "Can sell tickets"),
            ("cancel_ticket", "Can cancel tickets"),
            ("refund_ticket", "Can refund tickets (medical reasons)"),
            ("scan_ticket", "Can scan tickets at boarding"),
            ("view_documents", "Can view passenger document photos"),
            ("view_reports", "Can view sales reports"),
        ]

    def __str__(self):
        return self.serial

    @property
    def total(self):
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        if not self.serial:
            self.serial = self._new_serial()
        super().save(*args, **kwargs)

    @staticmethod
    def _new_serial():
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            s = "AP-" + "".join(secrets.choice(alphabet) for _ in range(8))
            if not Ticket.objects.filter(serial=s).exists():
                return s

    # --- QR code: "<serial>.<hmac>" so a scanner can verify authenticity even offline ---
    @staticmethod
    def sign(serial: str) -> str:
        key = settings.TICKET_SIGNING_KEY.encode()
        return hmac.new(key, serial.encode(), hashlib.sha256).hexdigest()[:16]

    @property
    def qr_payload(self) -> str:
        return f"{self.serial}.{self.sign(self.serial)}"

    @classmethod
    def verify_payload(cls, payload: str):
        """Return the serial if the signature is valid, else None."""
        serial, _, sig = payload.strip().partition(".")
        if serial and sig and hmac.compare_digest(sig, cls.sign(serial)):
            return serial
        return None


class Announcement(models.Model):
    title = models.CharField(max_length=150)
    body = models.TextField()
    sailing = models.ForeignKey(Sailing, null=True, blank=True, on_delete=models.SET_NULL, related_name="announcements")
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
