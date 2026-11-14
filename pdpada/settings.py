"""
Settings project PDPADA (Sistema Membru PD - Postu Dom Aleixo).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
	if DEBUG:
		SECRET_KEY = 'dev-only-key-ganti-di-produksi'
	else:
		raise RuntimeError('DJANGO_SECRET_KEY wajib diisi jika DEBUG=False')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]
# Contoh: https://USERNAME.pythonanywhere.com (wajib untuk login/form lewat HTTPS)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.humanize',
	'crispy_forms',
	'crispy_bootstrap4',
	'rest_framework',
	'main.apps.MainConfig',
	'custom.apps.CustomConfig',
	'config.apps.ConfigConfig',
	'users.apps.UsersConfig',
	'membro.apps.MembroConfig',
	'eleisaun.apps.EleisaunConfig',
	'report.apps.ReportConfig',
	'notification.apps.NotificationConfig',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pdpada.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
				'config.context_processors.ano_ativu',
			],
		},
	},
]

WSGI_APPLICATION = 'pdpada.wsgi.application'

if os.environ.get('DB_ENGINE', 'sqlite') == 'mysql':
	DATABASES = {
		'default': {
			'ENGINE': 'django.db.backends.mysql',
			'NAME': os.environ.get('DB_NAME', 'pdpada'),
			'USER': os.environ.get('DB_USER', 'root'),
			'PASSWORD': os.environ.get('DB_PASSWORD', ''),
			'HOST': os.environ.get('DB_HOST', 'localhost'),
			'PORT': os.environ.get('DB_PORT', '3306'),
			'CONN_MAX_AGE': 60,
		}
	}
else:
	DATABASES = {
		'default': {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': BASE_DIR / 'db.sqlite3',
		}
	}

AUTH_PASSWORD_VALIDATORS = [
	{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
	{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
	{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
	{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dili'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# File sensitif (foto dan kartu eleitoral): di luar MEDIA_ROOT, tanpa URL publik.
# Dilayani hanya lewat view ber-izin; ikut dicadangkan bersama database.
PRIVATE_ROOT = os.environ.get('DJANGO_PRIVATE_ROOT') or os.path.join(BASE_DIR, 'private')

# Batas ukuran upload (byte) yang disimpan di memori sebelum ke file sementara
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap4'
CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOGIN_REDIRECT_URL = 'home'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'login'

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
	message_constants.DEBUG: 'debug',
	message_constants.INFO: 'info',
	message_constants.SUCCESS: 'success',
	message_constants.WARNING: 'warning',
	message_constants.ERROR: 'danger',
}

REST_FRAMEWORK = {
	'DEFAULT_AUTHENTICATION_CLASSES': [
		'rest_framework.authentication.SessionAuthentication',
	],
	'DEFAULT_PERMISSION_CLASSES': [
		'rest_framework.permissions.IsAuthenticated',
	],
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sesi: otomatis keluar setelah 12 jam
SESSION_COOKIE_AGE = 60 * 60 * 12

# Cookie dan header keamanan dasar
SESSION_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
# HSTS dimatikan secara bawaan; isi DJANGO_HSTS_SECONDS (mis. 31536000) setelah HTTPS stabil
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '0') or 0)
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
	SESSION_COOKIE_SECURE = True
	CSRF_COOKIE_SECURE = True


# ---- Logging: konsol selalu; file berputar (5 MB x 5) saat produksi. Logger aplikasi: 'pdpada'.
LOG_DIR = Path(os.environ.get('DJANGO_LOG_DIR') or BASE_DIR / 'logs')
_log_handlers = {'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'}}
if not DEBUG:
	try:
		LOG_DIR.mkdir(parents=True, exist_ok=True)
		_log_handlers['file'] = {
			'class': 'logging.handlers.RotatingFileHandler', 'filename': str(LOG_DIR / 'app.log'),
			'maxBytes': 5 * 1024 * 1024, 'backupCount': 5, 'encoding': 'utf-8', 'formatter': 'simple'}
	except OSError:
		pass  # folder log tidak bisa dibuat: cukup log ke konsol (error log server)
LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {'simple': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'}},
	'handlers': _log_handlers,
	'loggers': {
		'django': {'handlers': list(_log_handlers), 'level': 'WARNING'},
		'pdpada': {'handlers': list(_log_handlers), 'level': 'INFO', 'propagate': False},
	},
}

# Kop surat dokumen resmi (PDF Lista Delegadu); bisa diubah lewat environment
PD_NAMA_SEKRETARIADO = os.environ.get('PD_NAMA_SEKRETARIADO', 'SEKRETARIADO PARTIDO DEMOCRÁTICO')
PD_POSTU = os.environ.get('PD_POSTU', 'Dom-Aleixo')
PD_ALAMAT = os.environ.get('PD_ALAMAT', 'Perumnas Bairo Ailok Laran')
PD_KONTAKTU = os.environ.get('PD_KONTAKTU', '+670 77279439 / +670 77332283')
