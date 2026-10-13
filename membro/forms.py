import datetime
from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML
from django.urls import reverse
from custom.models import Village, Aldeia, Organizasaun
from config import roles
from config.user_utils import c_user_group, c_user_scope
from membro.models import Membro, Alokasaun, POZISAUN_POR_NIVEL

BTN_CANCEL = """ <a class="btn btn-secondary" href="{{ cancel_url }}" title="Cancela"><i class="fa fa-close"></i> Cancela</a> """
BTN_SAVE = """ <button class="btn btn-primary" type="submit" title="Rai"> Rai <i class="fa fa-save"></i></button> """


class DateInput(forms.DateInput):
	input_type = 'date'

	def __init__(self, **kwargs):
		kwargs.setdefault('format', '%Y-%m-%d')
		super().__init__(**kwargs)


def normalize_eleitoral(value):
	return (value or '').strip().upper()


class MembroForm(forms.ModelForm):
	date_of_birth = forms.DateField(label="Data Moris", widget=DateInput(), required=True)
	data_hakbit = forms.DateField(label="Data Hakbit (Tama PD)", widget=DateInput(), required=False)

	class Meta:
		model = Membro
		fields = ['nome', 'sex', 'place_of_birth', 'date_of_birth', 'marital', 'nu_eleitoral', 'nu_bi',
			'telefone', 'image', 'village', 'aldeia', 'address', 'organizasaun', 'data_hakbit', 'status']

	def __init__(self, *args, user=None, **kwargs):
		super().__init__(*args, **kwargs)
		group = c_user_group(user) if user else None
		scope = c_user_scope(user) if user else None
		self.fields['organizasaun'].queryset = Organizasaun.objects.filter(is_active=True)
		self.fields['organizasaun'].empty_label = '--- Laiha ---'
		self.fields['village'].queryset = Village.objects.all()
		self.fields['aldeia'].queryset = Aldeia.objects.select_related('village')
		if group == roles.SEKR_SUKU and scope and scope.village_id:
			self.fields['village'].queryset = Village.objects.filter(pk=scope.village_id)
			self.fields['aldeia'].queryset = Aldeia.objects.filter(village_id=scope.village_id)
			self.fields['village'].initial = scope.village_id
			self.fields['village'].disabled = True
		elif group == roles.SEKR_ALDEIA and scope and scope.aldeia_id:
			self.fields['village'].queryset = Village.objects.filter(pk=scope.aldeia.village_id)
			self.fields['aldeia'].queryset = Aldeia.objects.filter(pk=scope.aldeia_id)
			self.fields['village'].initial = scope.aldeia.village_id
			self.fields['aldeia'].initial = scope.aldeia_id
			self.fields['village'].disabled = True
			self.fields['aldeia'].disabled = True
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.form_id = 'membroForm'
		self.helper.layout = Layout(
			Row(
				Column('nome', css_class='form-group col-md-6 mb-0'),
				Column('sex', css_class='form-group col-md-2 mb-0'),
				Column('nu_eleitoral', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('place_of_birth', css_class='form-group col-md-5 mb-0'),
				Column('date_of_birth', css_class='form-group col-md-3 mb-0'),
				Column('marital', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('nu_bi', css_class='form-group col-md-4 mb-0'),
				Column('telefone', css_class='form-group col-md-4 mb-0'),
				Column('image', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('village', css_class='form-group col-md-4 mb-0'),
				Column('aldeia', css_class='form-group col-md-4 mb-0'),
				Column('address', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('organizasaun', css_class='form-group col-md-4 mb-0'),
				Column('data_hakbit', css_class='form-group col-md-4 mb-0'),
				Column('status', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			HTML(BTN_CANCEL),
			HTML(BTN_SAVE)
		)

	def clean_nome(self):
		return ' '.join(self.cleaned_data['nome'].split())

	def clean_date_of_birth(self):
		dob = self.cleaned_data['date_of_birth']
		if dob > datetime.date.today():
			raise ValidationError('Data moris la bele iha futuru.')
		return dob

	def clean_nu_eleitoral(self):
		valor = normalize_eleitoral(self.cleaned_data['nu_eleitoral'])
		qs = Membro.objects.filter(nu_eleitoral__iexact=valor)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		dup = qs.select_related('village', 'aldeia').first()
		if dup:
			raise ValidationError(
				f'DUPLIKADU! Nu. Eleitoral {valor} registu ona ba {dup.nome} '
				f'iha Suku {dup.village}, Aldeia {dup.aldeia}. Ida ida deit bele vota.')
		return valor

	def clean(self):
		cleaned = super().clean()
		village, aldeia = cleaned.get('village'), cleaned.get('aldeia')
		if village and aldeia and aldeia.village_id != village.pk:
			self.add_error('aldeia', 'Aldeia ne\'e la pertense ba suku ne\'ebé hili.')
		return cleaned


class RejeitaForm(forms.Form):
	razaun = forms.CharField(label="Razaun Rejeita", min_length=5, widget=forms.Textarea(attrs={'rows': 4}))

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.layout = Layout(
			'razaun',
			HTML(BTN_CANCEL),
			HTML(""" <button class="btn btn-danger" type="submit" title="Rejeita"> Rejeita <i class="fa fa-times"></i></button> """)
		)


class MembroChoiceField(forms.ModelChoiceField):
	def label_from_instance(self, obj):
		return f'{obj.nome} ({obj.nu_eleitoral}) - {obj.village}/{obj.aldeia}'


class AlokasaunForm(forms.ModelForm):
	membro = MembroChoiceField(label="Membru", queryset=Membro.objects.none())
	data_hahu = forms.DateField(label="Data Hahu", widget=DateInput())
	data_termina = forms.DateField(label="Data Termina", widget=DateInput(), required=False)

	class Meta:
		model = Alokasaun
		fields = ['membro', 'nivel', 'pozisaun', 'village', 'aldeia', 'organizasaun', 'data_hahu', 'data_termina', 'ativu']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['membro'].queryset = Membro.objects.filter(
			aprovasaun='Aprovadu', status='Ativu').select_related('village', 'aldeia')
		self.fields['organizasaun'].queryset = Organizasaun.objects.filter(is_active=True)
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.form_id = 'alokasaunForm'
		self.helper.attrs = {'data-aldeias-url': reverse('ajax_load_aldeias')}
		self.helper.layout = Layout(
			Row(Column('membro', css_class='form-group col-md-12 mb-0'), css_class='form-row'),
			Row(
				Column('nivel', css_class='form-group col-md-6 mb-0'),
				Column('pozisaun', css_class='form-group col-md-6 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('village', css_class='form-group col-md-4 mb-0 unit-suku unit-aldeia'),
				Column('aldeia', css_class='form-group col-md-4 mb-0 unit-aldeia'),
				Column('organizasaun', css_class='form-group col-md-4 mb-0 unit-organizasaun'),
				css_class='form-row'
			),
			Row(
				Column('data_hahu', css_class='form-group col-md-4 mb-0'),
				Column('data_termina', css_class='form-group col-md-4 mb-0'),
				Column('ativu', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			HTML(BTN_CANCEL),
			HTML(BTN_SAVE)
		)

	def clean(self):
		cleaned = super().clean()
		membro, nivel, pozisaun = cleaned.get('membro'), cleaned.get('nivel'), cleaned.get('pozisaun')
		if not (membro and nivel and pozisaun):
			return cleaned
		if pozisaun not in POZISAUN_POR_NIVEL[nivel]:
			self.add_error('pozisaun', f'Pozisaun {pozisaun} la existe iha nivel {nivel}.')
			return cleaned
		village, aldeia, org = cleaned.get('village'), cleaned.get('aldeia'), cleaned.get('organizasaun')
		if nivel == 'Postu':
			village = aldeia = org = None
		elif nivel == 'Suku':
			aldeia = org = None
			if not village:
				self.add_error('village', 'Suku tenke hili.')
			elif membro.village_id != village.pk:
				self.add_error('membro', 'Membru ne\'e la hela iha suku ne\'e.')
		elif nivel == 'Aldeia':
			org = None
			if not aldeia:
				self.add_error('aldeia', 'Aldeia tenke hili.')
			elif membro.aldeia_id != aldeia.pk:
				self.add_error('membro', 'Membru ne\'e la hela iha aldeia ne\'e.')
			else:
				village = aldeia.village
		elif nivel == 'Organizasaun':
			village = aldeia = None
			if not org:
				self.add_error('organizasaun', 'Organizasaun tenke hili.')
			elif membro.organizasaun_id != org.pk:
				self.add_error('membro', 'Membru ne\'e la tama organizasaun ne\'e.')
		cleaned['village'], cleaned['aldeia'], cleaned['organizasaun'] = village, aldeia, org
		if cleaned.get('data_termina') and cleaned.get('data_hahu') and cleaned['data_termina'] < cleaned['data_hahu']:
			self.add_error('data_termina', 'Data termina tenke depois data hahu.')
		if cleaned.get('ativu') == 'Sim' and not self.errors:
			qs = Alokasaun.objects.filter(nivel=nivel, pozisaun=pozisaun, ativu='Sim')
			if nivel == 'Suku':
				qs = qs.filter(village=village)
			elif nivel == 'Aldeia':
				qs = qs.filter(aldeia=aldeia)
			elif nivel == 'Organizasaun':
				qs = qs.filter(organizasaun=org)
			if self.instance.pk:
				qs = qs.exclude(pk=self.instance.pk)
			atual = qs.select_related('membro').first()
			if atual:
				raise ValidationError(f'{pozisaun} {nivel} ativu iha ona: {atual.membro.nome}. Halo nia la ativu uluk.')
		return cleaned
