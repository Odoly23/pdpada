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
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils.cache import add_never_cache_headers

FIELD = '_ftoken'
SESSION_KEY = '_ftokens'
MAX_TOKENS = 100
TOKEN_TTL = 60 * 60 * 6  # Tiket validu durante oras 6

# <form ... method="post" ...> (la inklui formuláriu ho data-once="off")
FORM_RE = re.compile(
    r'<form\b(?=[^>]*\bmethod\s*=\s*["\']?post)(?![^>]*\bdata-once\s*=\s*["\']?off)[^>]*>',
    re.I,
)

# Kaminu ne'ebé la presiza tiket (ezemplu: API DRF, logout, admin Django)
EXEMPT_PREFIXES = (
    '/api/',
    '/admin/',
)

MSG_USED = "Formuláriu ne'e uza ona. Dadus la rai dala rua; ida ne'e formuláriu foun."


class OneTimeFormMiddleware:
    """Kontrola formuláriu POST: tiket úniku, uza dala ida de'it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'ONE_TIME_FORMS', True) or not self._ativu(request):
            return self.get_response(request)

        if request.method == 'POST' and not self._izentu(request):
            token = request.POST.get(FIELD, '').strip()
            if not token or not self._konsume(request, token):
                messages.warning(request, MSG_USED)
                return HttpResponseRedirect(request.get_full_path())

        response = self.get_response(request)
        return self._injeta(request, response)

    @staticmethod
    def _ativu(request):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    @staticmethod
    def _izentu(request):
        # Ignora API, Admin, ka request AJAX/JSON
        if any(request.path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return True
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        return False

    @staticmethod
    def _cache_key(user_id, token):
        return f'ftoken:{user_id}:{token}'

    def _konsume(self, request, token):
        # 1. Tenta uza cache atómiku (prevene double-click iha milisegundu nia laran)
        ckey = self._cache_key(request.user.pk, token)
        if cache.delete(ckey):
            self._hamoos_husi_session(request, token)
            return True

        # 2. Fallback ba session se cache laiha ka reset
        return self._hamoos_husi_session(request, token, save_now=True)

    @staticmethod
    def _hamoos_husi_session(request, token, save_now=False):
        tokens = request.session.get(SESSION_KEY, [])
        if token in tokens:
            tokens.remove(token)
            request.session[SESSION_KEY] = tokens
            if save_now:
                request.session.save()
            return True
        return False

    def _injeta(self, request, response):
        ctype = response.get('Content-Type', '')
        if (
            getattr(response, 'streaming', False)
            or response.status_code != 200
            or not ctype.startswith('text/html')
            or not self._ativu(request)
            or self._izentu(request)
        ):
            return response

        charset = response.charset or 'utf-8'
        try:
            html = response.content.decode(charset)
        except UnicodeDecodeError:
            return response

        novu = []

        def tambah(m):
            token = secrets.token_urlsafe(24)
            novu.append(token)
            cache.set(self._cache_key(request.user.pk, token), 1, TOKEN_TTL)
            return f'{m.group(0)}<input type="hidden" name="{FIELD}" value="{token}">'

        html = FORM_RE.sub(tambah, html)
        if not novu:
            return response

        tokens = (request.session.get(SESSION_KEY, []) + novu)[-MAX_TOKENS:]
        request.session[SESSION_KEY] = tokens

        response.content = html.encode(charset)
        if 'Content-Length' in response:
            response['Content-Length'] = len(response.content)

        # Pájina ho formuláriu la rai iha cache: "Back" mak foti formuláriu foun
        add_never_cache_headers(response)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
