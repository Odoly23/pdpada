from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from fleet.models import Route
from ticketing.models import Announcement, Fare, Sailing


def landing(request):
    """Public page: upcoming sailings, fares and announcements. No login needed for passengers."""
    sailings = (
        Sailing.objects.filter(departure__gte=timezone.now() - timedelta(hours=1))
        .exclude(status=Sailing.Status.COMPLETED)
        .select_related("vessel__operator", "route__origin", "route__destination")
        .prefetch_related("quotas")[:30]
    )
    fares = (
        Fare.objects.filter(item__is_active=True, route__is_active=True)
        .select_related("route__origin", "route__destination", "item")
        .order_by("route__origin__name", "item__quota_group", "item__sort_order")
    )
    announcements = Announcement.objects.filter(is_public=True)[:5]
    return render(
        request,
        "core/landing.html",
        {"sailings": sailings, "fares": fares, "announcements": announcements, "routes": Route.objects.filter(is_active=True)},
    )


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")
