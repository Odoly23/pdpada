import logging
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from config import roles
from config.user_utils import c_user_group
from notification.utils import notif_counts

logger = logging.getLogger('pdpada')
ROLE_NAME = dict(roles.ROLE_LABELS)

LOGIN_MAX_FAILS = 5            # percobaan gagal sebelum dikunci
LOGIN_LOCK_SECONDS = 15 * 60   # lama kunci (detik)


class ThrottledLoginView(LoginView):
	"""Login dengan pembatasan percobaan gagal per (alamat, username): 5 kali dalam 15 menit."""
	template_name = 'home/login.html'
	redirect_authenticated_user = True

	def _key(self):
		username = (self.request.POST.get('username') or '').strip().lower()[:150]
		return f"login-fail:{self.request.META.get('REMOTE_ADDR', '')}:{username}"

	def post(self, request, *args, **kwargs):
		if cache.get(self._key(), 0) >= LOGIN_MAX_FAILS:
			logger.warning('login diblokir sementara: %s', self._key())
			form = AuthenticationForm(request=request)
			return self.render_to_response(self.get_context_data(form=form, throttled=True), status=429)
		return super().post(request, *args, **kwargs)

	def form_invalid(self, form):
		cache.add(self._key(), 0, LOGIN_LOCK_SECONDS)
		try:
			cache.incr(self._key())
		except ValueError:  # kunci kedaluwarsa di antara dua panggilan
			cache.set(self._key(), 1, LOGIN_LOCK_SECONDS)
		return super().form_invalid(form)

	def form_valid(self, form):
		cache.delete(self._key())
		return super().form_valid(form)


def _tiles(group, counts):
	"""Pintasan beranda sesuai peran: (judul, keterangan, ikon, url, badge)."""
	tiles = []

	def add(title, desc, icon, url, badge=0):
		tiles.append({'title': title, 'desc': desc, 'icon': icon, 'url': url, 'badge': badge})

	if group == roles.ADMIN:
		add('Painel Admin', 'Sumariu uzuáriu no data master', 'fa-tachometer', reverse('user-painel'))
		add('Uzuáriu', 'Kria no jere konta ho peran no suku', 'fa-users', reverse('user-list'))
		add('Suku no Aldeia', 'Rejistu suku Postu Dom Aleixo', 'fa-map-marker', reverse('master-list', args=['suku']))
		add('Organizasaun', 'OJD, OPD, MPD no seluk', 'fa-flag', reverse('master-list', args=['organizasaun']))
		add('Tinan Ativu', 'Troka tinan ne\'ebé uza ba relatoriu', 'fa-calendar', reverse('master-list', args=['ano']))
		add('Historia', 'Rekorda mudansa dadus tomak', 'fa-history', reverse('historia-list'))
		return tiles
	if group not in roles.VIEW_ROLES:
		return tiles
	add('Painel Membru', 'Total, sexu no aprovasaun tuir suku', 'fa-tachometer', reverse('membro-painel'))
	if group in roles.LISTA_ROLES:
		add('Lista Membru', 'Hare, filtra no hili dadus membru', 'fa-list', reverse('membro-list'))
	if group in roles.INPUT_ROLES:
		add('Aumenta Membru', 'Rejistu membru foun', 'fa-user-plus', reverse('membro-add'))
		add('Membru Rejeitadu', 'Koriji dadus ne\'ebé rejeitadu', 'fa-exclamation-triangle',
			reverse('membro-list') + '?aprovasaun=Rejeitadu&ano=hotu', counts['rejeitadu'])
	if group in roles.APROVA_ROLES:
		add('Hein Aprovasaun', 'Aprova ka rejeita membru foun', 'fa-check-square-o', reverse('aprovasaun-list'), counts['pendente'])
	if group in roles.LISTA_ROLES:
		add('Pesquiza', 'Buka membru ho lalais', 'fa-search', reverse('membro-cari'))
	if group in roles.DUPLIKAT_ROLES:
		add('Dupla Potensial', 'Verifika membru ne\'ebé bele dupla', 'fa-clone', reverse('membro-dupla'))
	add('Relatoriu Tabular', 'Tabela rekapitulasaun ho tautan', 'fa-table', reverse('report-dash'))
	add('Relatoriu Grafiku', 'Grafiku membru tuir kategoria', 'fa-bar-chart', reverse('report-chart'))
	if group in roles.STRUKTURA_ROLES:
		add('Struktura PD', 'Coordenador no Sekretariu tuir nivel', 'fa-sitemap', reverse('alokasaun-dash'))
	if group in roles.HISTORIA_ROLES:
		add('Historia', 'Rekorda mudansa dadus', 'fa-history', reverse('historia-list'))
	return tiles


@login_required
def home(request):
	"""Beranda ringan: sambutan, pencarian, dan pintasan sesuai peran (tanpa query berat)."""
	group = c_user_group(request.user)
	if group in roles.POSTU_ROLES:  # peran Postu: Varanda rekapitulasi (total, suku, aldeia, grafik)
		from membro.views.rekap_v import VarandaPostu
		return VarandaPostu(request)
	_, counts = notif_counts(request.user)
	context = {
		'group': group, 'role_label': ROLE_NAME.get(group, ''),
		'tiles': _tiles(group, counts), 'can_search': group in roles.LISTA_ROLES, 'notif_counts': counts,
		'title': 'Varanda', 'legend': 'Varanda',
		'meta_description': 'SGDM-PDPADA: Sistema Jestaun Dadus Membru Partido Democratico, Postu Administrativu Dom Aleixo, Dili.',
	}
	return render(request, 'home/home.html', context)


def robots_txt(request):
	"""Sistem privat: larang semua mesin pencari."""
	return HttpResponse('User-agent: *\nDisallow: /\n', content_type='text/plain')


def healthz(request):
	"""Pemeriksaan kesehatan untuk pemantauan (tanpa login, tanpa data sensitif)."""
	try:
		with connection.cursor() as cursor:
			cursor.execute('SELECT 1')
			cursor.fetchone()
		db = 'ok'
	except Exception:  # noqa: BLE001 - laporan kesehatan harus selalu menjawab
		logger.exception('healthz: database tidak dapat diakses')
		db = 'error'
	status = 200 if db == 'ok' else 503
	return JsonResponse({'app': 'SGDM-PDPADA', 'status': 'ok' if db == 'ok' else 'error', 'database': db}, status=status)


def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	return render(request, 'home/500.html', status=500)
