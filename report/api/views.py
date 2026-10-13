from django.db.models import Count
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from config import roles
from config.user_utils import c_user_group, membro_ativu


class IsViewRole(BasePermission):
	def has_permission(self, request, view):
		return bool(request.user and request.user.is_authenticated and c_user_group(request.user) in roles.VIEW_ROLES)


class BaseAPI(APIView):
	authentication_classes = [SessionAuthentication]
	permission_classes = [IsAuthenticated, IsViewRole]

	def grouped(self, field):
		qs = membro_ativu(self.request.user).values_list(field).annotate(n=Count('id')).order_by(field)
		return [str(x[0]) if x[0] is not None else 'Laiha' for x in qs], [x[1] for x in qs]


class APIGender(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('sex')
		return Response({'label': label, 'obj': obj})


class APIAprovasaun(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('aprovasaun')
		return Response({'label': label, 'obj': obj})


class APISuku(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('village__name')
		return Response({'label': label, 'obj': obj})


class APIOrganizasaun(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('organizasaun__code')
		return Response({'label': label, 'obj': obj})
