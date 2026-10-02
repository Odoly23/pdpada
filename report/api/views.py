from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from report.services import summary


class CanViewReport(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('membro.view_report')


class APIMembruSumariu(APIView):
    """Label/obj ba chart (tuir eskopu user)."""
    permission_classes = [IsAuthenticated, CanViewReport]

    def get(self, request, format=None):
        s = summary(request.user)
        return Response({
            'group_label': s['group_label'],
            'label': [r['nome'] for r in s['rows']],
            'mane': [r['mane'] for r in s['rows']],
            'feto': [r['feto'] for r in s['rows']],
            'estadu': s['estadu'],
        })
