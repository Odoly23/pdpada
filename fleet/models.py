from django.db import models
from django.utils.translation import gettext_lazy as _


class Port(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(_("Naran"), max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Route(models.Model):
    origin = models.ForeignKey(Port, on_delete=models.PROTECT, related_name="departures")
    destination = models.ForeignKey(Port, on_delete=models.PROTECT, related_name="arrivals")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["origin__name", "destination__name"]
        constraints = [models.UniqueConstraint(fields=["origin", "destination"], name="uniq_route")]

    def __str__(self):
        return f"{self.origin} ➔ {self.destination}"


class Operator(models.Model):
    name = models.CharField(_("Naran"), max_length=150, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vessel(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name="vessels")
    name = models.CharField(_("Naran"), max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["operator", "name"], name="uniq_vessel_per_operator")]

    def __str__(self):
        return self.name
