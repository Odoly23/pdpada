from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session

# model bawaan Django (model aplikasi iha admin.py ida-idak: custom, membro, eleisaun, users)
admin.site.register(LogEntry)
admin.site.register(Permission)
admin.site.register(ContentType)
admin.site.register(Session)
