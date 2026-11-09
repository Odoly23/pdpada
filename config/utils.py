import hmac
import hashlib
from django.conf import settings


def hash_id(value):
	"""HMAC-SHA256 (64 karakter hex) dengan kunci SECRET_KEY. Dipakai untuk hashid di URL."""
	return hmac.new(settings.SECRET_KEY.encode(), str(value).encode(), hashlib.sha256).hexdigest()


def getlastid(table_name):
	result = table_name.objects.last()
	if result:
		lastid = result.id
		newid = lastid + 1
	else:
		lastid = 0
		newid = 1
	return lastid, newid


def getnewid(table_name):
	result = table_name.objects.last()
	newid = result.id + 1 if result else 1
	return newid, hash_id(f'{table_name._meta.label}:{newid}')


def getjustnewid(table_name):
	result = table_name.objects.last()
	return result.id + 1 if result else 1


def split_string(string):
	return string.split()[0].lower()


MONTHS = ['Janeiru', 'Fevreiru', 'Marsu', 'Abril', 'Maiu', 'Junhu',
	'Julhu', 'Agustu', 'Setembru', 'Outubru', 'Novembru', 'Dezembru']


def getMonthName(num):
	return MONTHS[num - 1]
