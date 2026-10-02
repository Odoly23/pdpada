from django.shortcuts import render

from config.decorators import perm_required
from report.services import summary


@perm_required('membro.view_report')
def dashboard(request):
    data = summary(request.user)
    return render(request, 'report/dash.html', {'legend': 'Dashboard Membru', **data})
