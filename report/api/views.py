import datetime
from django.db.models import Count
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from config import roles
from config.user_utils import c_user_group, membro_ativu, alokasaun_scope


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


class APIAldeia(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('aldeia__name')
		return Response({'label': label, 'obj': obj})


class APIStatus(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('status')
		return Response({'label': label, 'obj': obj})


class APIMarital(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('marital')
		return Response({'label': label, 'obj': obj})


class APIHakbit(BaseAPI):
	"""Membru tuir tinan tama PD (tinan data_hakbit); ne'ebé laiha data la konta."""
	def get(self, request, format=None):
		qs = membro_ativu(request.user).filter(data_hakbit__isnull=False)
		rows = qs.values_list('data_hakbit__year').annotate(n=Count('id')).order_by('data_hakbit__year')
		return Response({'label': [str(r[0]) for r in rows], 'obj': [r[1] for r in rows]})


from membro.utils import AGE_BINS


class APIAge(BaseAPI):
	def get(self, request, format=None):
		today = datetime.date.today()
		counts = [0] * len(AGE_BINS)
		for dob in membro_ativu(request.user).values_list('date_of_birth', flat=True):
			age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
			for i, (lo, hi, _) in enumerate(AGE_BINS):
				if lo <= age <= hi:
					counts[i] += 1
					break
		return Response({'label': [b[2] for b in AGE_BINS], 'obj': counts})


class APIAlokasaun(BaseAPI):
	"""Posisi aktif per nivel dan pozisaun (untuk grafik Struktura)."""
	def get(self, request, format=None):
		order = {'Postu': 0, 'Suku': 1, 'Aldeia': 2, 'Organizasaun': 3}
		poz = {'Presidente': 0, 'Coordenador': 1, 'Sekretariu': 2}
		rows = alokasaun_scope(request.user).filter(ativu='Sim').values_list('nivel', 'pozisaun').annotate(n=Count('id'))
		rows = sorted(rows, key=lambda r: (order.get(r[0], 9), poz.get(r[1], 9)))
		return Response({'label': [f'{r[0]} · {r[1]}' for r in rows], 'obj': [r[2] for r in rows]})
