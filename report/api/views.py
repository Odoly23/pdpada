import datetime
from django.db.models import Count
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from config import roles
from config.user_utils import c_user_group, membro_ativu, alokasaun_scope


# permisaun: de'it papél ne'ebé bele haree relatóriu
class IsViewRole(BasePermission):
	def has_permission(self, request, view):
		return bool(request.user and request.user.is_authenticated and c_user_group(request.user) in roles.VIEW_ROLES)


# bazu API relatóriu (eskopu tuir permisaun)
class BaseAPI(APIView):
	authentication_classes = [SessionAuthentication]
	permission_classes = [IsAuthenticated, IsViewRole]

	def grouped(self, field):
		qs = membro_ativu(self.request.user).values_list(field).annotate(n=Count('id')).order_by(field)
		return [str(x[0]) if x[0] is not None else 'Laiha' for x in qs], [x[1] for x in qs]


# API sexu
class APIGender(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('sex')
		return Response({'label': label, 'obj': obj})


# API estadu aprovasaun
class APIAprovasaun(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('aprovasaun')
		return Response({'label': label, 'obj': obj})


# API membru tuir suku
class APISuku(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('village__name')
		return Response({'label': label, 'obj': obj})


# API membru tuir organizasaun
class APIOrganizasaun(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('organizasaun__code')
		return Response({'label': label, 'obj': obj})


# API membru tuir aldeia
class APIAldeia(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('aldeia__name')
		return Response({'label': label, 'obj': obj})


# API estadu membru (ativu/la ativu)
class APIStatus(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('status')
		return Response({'label': label, 'obj': obj})


# API estadu sivíl
class APIMarital(BaseAPI):
	def get(self, request, format=None):
		label, obj = self.grouped('marital')
		return Response({'label': label, 'obj': obj})


# API tinan hakbit (tama partidu)
class APIHakbit(BaseAPI):
	"""Membru tuir tinan tama PD (tinan data_hakbit); ne'ebé laiha data la konta."""
	def get(self, request, format=None):
		qs = membro_ativu(request.user).filter(data_hakbit__isnull=False)
		rows = qs.values_list('data_hakbit__year').annotate(n=Count('id')).order_by('data_hakbit__year')
		return Response({'label': [str(r[0]) for r in rows], 'obj': [r[1] for r in rows]})


from membro.utils import AGE_BINS


# API grupu idade
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


# API alokasaun
class APIAlokasaun(BaseAPI):
	"""Posisi aktif per nivel dan pozisaun (untuk grafik Struktura)."""
	def get(self, request, format=None):
		order = {'Postu': 0, 'Suku': 1, 'Aldeia': 2, 'Organizasaun': 3}
		from membro.models import Pozisaun
		poz = {p.naran: p.urutan for p in Pozisaun.objects.all()}
		rows = alokasaun_scope(request.user).filter(ativu='Sim').values_list('nivel', 'pozisaun').annotate(n=Count('id'))
		rows = sorted(rows, key=lambda r: (order.get(r[0], 9), poz.get(r[1], 9)))
		return Response({'label': [f'{r[0]} · {r[1]}' for r in rows], 'obj': [r[2] for r in rows]})


# API suku no sexu
class APISukuSexu(BaseAPI):
	"""Perbandingan Mane dan Feto per suku (grafik berkelompok)."""
	def get(self, request, format=None):
		from django.db.models import Q
		rows = membro_ativu(request.user).order_by().values('village__name').annotate(
			mane=Count('id', filter=Q(sex='Mane')), feto=Count('id', filter=Q(sex='Feto'))).order_by('village__name')
		return Response({'label': [r['village__name'] for r in rows], 'mane': [r['mane'] for r in rows], 'feto': [r['feto'] for r in rows]})


# API kategoria (Militante, Simpatizante, Struktura Penting)
class APIJenis(BaseAPI):
	"""Struktura penting, Militante dan Simpatizante (tiga data separadu)."""
	def get(self, request, format=None):
		from membro.utils import filter_jenis
		qs = membro_ativu(request.user)
		labels = [('Struktura', 'Struktura Penting'), ('Militante', 'Militante'), ('Simpatizante', 'Simpatizante')]
		return Response({'label': [l for _, l in labels], 'obj': [filter_jenis(qs, v).count() for v, _ in labels]})


# API estadu servisu (Governu, Organizasaun, Kompañia, Seidauk)
class APIServisu(BaseAPI):
	def get(self, request, format=None):
		qs = membro_ativu(request.user)
		rows = [('Servisu Governu', qs.filter(servisu__status='Servisu', servisu__setor='Governu')),
			('Servisu Organizasaun', qs.filter(servisu__status='Servisu', servisu__setor='Organizasaun')),
			('Servisu Kompañia', qs.filter(servisu__status='Servisu', servisu__setor='Kompania')),
			('Seidauk Servisu', qs.filter(servisu__status='Seidauk')), ('Seidauk iha dadus', qs.filter(servisu__isnull=True))]
		return Response({'label': [l for l, _ in rows], 'obj': [q.count() for _, q in rows]})

