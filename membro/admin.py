from django import forms
from django.contrib import admin
from .models import Membro, Alokasaun, Historia, OrgPozisaun, OrgResponsavel, Edukasaun, Servisu, Pozisaun


class AlokasaunAdminForm(forms.ModelForm):
	"""Pozisaun iha admin Alokasaun hili husi tabela Pozisaun (Coordenador, Vice I-III, ...)."""
	pozisaun = forms.ChoiceField(label="Pozisaun")

	class Meta:
		model = Alokasaun
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		nomes = list(Pozisaun.objects.filter(ativu=True).values_list('naran', flat=True))
		if self.instance.pk and self.instance.pozisaun not in nomes:
			nomes.append(self.instance.pozisaun)
		self.fields['pozisaun'].choices = [('', '---------')] + [(n, n) for n in nomes]


@admin.register(Alokasaun)
class AlokasaunAdmin(admin.ModelAdmin):
	form = AlokasaunAdminForm
	list_display = ('membro', 'nivel', 'pozisaun', 'village', 'aldeia', 'organizasaun', 'ativu')
	list_filter = ('nivel', 'pozisaun', 'ativu')


@admin.register(Pozisaun)
class PozisaunAdmin(admin.ModelAdmin):
	list_display = ('naran', 'urutan', 'iha_postu', 'iha_suku', 'iha_aldeia', 'iha_organizasaun', 'ativu')
	list_editable = ('urutan', 'ativu')

	def get_readonly_fields(self, request, obj=None):
		return ('naran',) if obj else ()  # Alokasaun rai naran ne'e: la bele troka bainhira iha ona

	def has_delete_permission(self, request, obj=None):
		if obj and Alokasaun.objects.filter(pozisaun=obj.naran).exists():
			return False  # pozisaun uza ona iha Alokasaun
		return super().has_delete_permission(request, obj)


admin.site.register(Membro)
admin.site.register(Historia)
admin.site.register(OrgPozisaun)
admin.site.register(OrgResponsavel)
admin.site.register(Edukasaun)
admin.site.register(Servisu)
