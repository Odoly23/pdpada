"""Middleware kustomizadu: formuláriu uza dala ida de'it.

Razaun: se uzuáriu klik "Back" iha browser depois de rai dadus, formuláriu antigu
bele hatudu fali dadus tuan no bele rai dala rua. Middleware ne'e fó "tiket" úniku
ba formuláriu POST ida-idak; tiket uza ona la valór tan. Pájina ho formuláriu mós
la rai iha cache, né'e duke "Back" browser foti formuláriu foun (dadus foun).
"""
import re
import secrets

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.cache import add_never_cache_headers

FIELD = '_ftoken'
SESSION_KEY = '_ftokens'
MAX_TOKENS = 100

# <form ... method="post" ...> (la inklui formuláriu ho data-once="off")
FORM_RE = re.compile(r'<form\b(?=[^>]*\bmethod\s*=\s*["\']?post)(?![^>]*\bdata-once\s*=\s*["\']?off)[^>]*>', re.I)

MSG_USED = 'Formuláriu ne\'e uza ona. Dadus la rai dala rua; ida ne\'e formuláriu foun.'


class OneTimeFormMiddleware:
	# Kontrola formuláriu POST: tiket úniku, uza dala ida de'it.

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if not getattr(settings, 'ONE_TIME_FORMS', True) or not self._ativu(request):
			return self.get_response(request)

		if request.method == 'POST' and FIELD in request.POST:
			if not self._konsume(request, request.POST.get(FIELD, '')):
				# tiket uza ona (double-submit ka "Back"): la rai, fila ba formuláriu foun
				messages.warning(request, MSG_USED)
				return HttpResponseRedirect(request.get_full_path())

		response = self.get_response(request)
		return self._injeta(request, response)

	@staticmethod
	def _ativu(request):
		user = getattr(request, 'user', None)
		return bool(user and user.is_authenticated)

	@staticmethod
	def _konsume(request, token):
		tokens = request.session.get(SESSION_KEY, [])
		if token in tokens:
			tokens.remove(token)
			request.session[SESSION_KEY] = tokens
			return True
		return False

	def _injeta(self, request, response):
		ctype = response.get('Content-Type', '')
		if (response.streaming or response.status_code != 200 or not ctype.startswith('text/html')
				or not self._ativu(request)):
			return response
		html = response.content.decode(response.charset or 'utf-8')
		novu = []

		def tambah(m):
			token = secrets.token_urlsafe(24)
			novu.append(token)
			return '%s<input type="hidden" name="%s" value="%s">' % (m.group(0), FIELD, token)

		html = FORM_RE.sub(tambah, html)
		if not novu:
			return response
		tokens = (request.session.get(SESSION_KEY, []) + novu)[-MAX_TOKENS:]
		request.session[SESSION_KEY] = tokens
		response.content = html.encode(response.charset or 'utf-8')
		# pájina ho formuláriu la rai iha cache: "Back" mak foti formuláriu foun
		add_never_cache_headers(response)
		response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
		return response
