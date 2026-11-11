from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from config import roles
from config.user_utils import c_user_group
from membro.utils import search_membro

SUGGEST_LIMIT = 8


class IsViewRole(BasePermission):
	def has_permission(self, request, view):
		return c_user_group(request.user) in roles.LISTA_ROLES


class APIMembroCari(APIView):
	"""Saran pencarian (typeahead): hanya membru dalam wilayah user, maksimal 8."""
	authentication_classes = [SessionAuthentication]
	permission_classes = [IsAuthenticated, IsViewRole]

	def get(self, request, format=None):
		results = search_membro(request.user, request.GET.get('q', ''), limit=SUGGEST_LIMIT)
		return Response([{
			'nome': m.nome, 'nu_eleitoral': m.nu_eleitoral, 'suku': str(m.village), 'aldeia': str(m.aldeia),
			'status': m.status, 'aprovasaun': m.aprovasaun, 'url': reverse('membro-detail', args=[m.hashed]),
		} for m in results])
