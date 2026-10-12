from django.contrib import admin

from .models import Operator, Port, Route, Vessel

for m in (Port, Route, Operator, Vessel):
    admin.site.register(m)
