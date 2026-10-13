from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML
from custom.models import Village, Aldeia, Organizasaun, Year

BTN_CANCEL = """ <a class="btn btn-secondary" href="{{ cancel_url }}" title="Cancela"><i class="fa fa-close"></i> Cancela</a> """
BTN_SAVE = """ <button class="btn btn-primary" type="submit" title="Rai"> Rai <i class="fa fa-save"></i></button> """


class MasterForm(forms.ModelForm):
	columns = []

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.layout = Layout(
			Row(*[Column(c, css_class='form-group col-md-4 mb-0') for c in self.columns], css_class='form-row'),
			HTML(BTN_CANCEL),
			HTML(BTN_SAVE)
		)

	def clean_name(self):
		return ' '.join(self.cleaned_data['name'].split())


class VillageForm(MasterForm):
	columns = ['name']

	class Meta:
		model = Village
		fields = ['name']


class AldeiaForm(MasterForm):
	columns = ['village', 'name']

	class Meta:
		model = Aldeia
		fields = ['village', 'name']

	def clean(self):
		cleaned = super().clean()
		village, name = cleaned.get('village'), cleaned.get('name')
		if village and name:
			qs = Aldeia.objects.filter(village=village, name__iexact=name)
			if self.instance.pk:
				qs = qs.exclude(pk=self.instance.pk)
			if qs.exists():
				self.add_error('name', 'Aldeia ho naran ne\'e iha ona iha suku ne\'e.')
		return cleaned


class OrganizasaunForm(MasterForm):
	columns = ['code', 'name', 'is_active']

	class Meta:
		model = Organizasaun
		fields = ['code', 'name', 'is_active']

	def clean_code(self):
		code = self.cleaned_data['code'].strip().upper()
		qs = Organizasaun.objects.filter(code__iexact=code)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise forms.ValidationError('Kódigu ne\'e iha ona.')
		return code


class YearForm(MasterForm):
	columns = ['year', 'is_active']

	class Meta:
		model = Year
		fields = ['year', 'is_active']
