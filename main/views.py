from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from report.services import summary


@login_required
def home(request):
    ctx = {'legend': 'Varanda'}
    if request.user.has_perm('membro.view_report'):
        ctx.update(summary(request.user))
    return render(request, 'home/home.html', ctx)


def error_403(request, exception=None):
    return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
    return render(request, 'home/404.html', status=404)


def error_500(request):
    return render(request, 'home/500.html', status=500)
