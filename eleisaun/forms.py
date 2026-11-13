from django import forms
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML
from config import roles
from config.file_utils import sanitize_image, validate_image_content, validate_pdf_content, validate_pdf_size
from config.upload_utils import validate_image_size
from custom.models import Aldeia
from eleisaun.models import Eleisaun, TempatVoting, FiskaisTempat, Resultado
from membro.forms import BTN_CANCEL, BTN_SAVE


def _helper(*fields):
	helper = FormHelper()
	helper.form_method = 'post'
	helper.layout = Layout(*fields, HTML(BTN_CANCEL), HTML(BTN_SAVE))
	return helper


class EleisaunForm(forms.ModelForm):
	class Meta:
		model = Eleisaun
		fields = ['naran', 'tinan', 'ativu']
		help_texts = {'ativu': 'Se hili, dashboard live loke no eleisaun seluk taka otomatikamente.'}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.helper = _helper(Row(Column('naran', css_class='form-group col-md-6 mb-0'), Column('tinan', css_class='form-group col-md-3 mb-0'),
			Column('ativu', css_class='form-group col-md-3 mb-0'), css_class='form-row'))


class TempatForm(forms.ModelForm):
	class Meta:
		model = TempatVoting
		fields = ['naran', 'village', 'aldeia', 'ativu']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['aldeia'].queryset = Aldeia.objects.select_related('village')
		self.fields['aldeia'].required = False
		self.helper = _helper(Row(Column('naran', css_class='form-group col-md-4 mb-0'), Column('village', css_class='form-group col-md-3 mb-0'),
			Column('aldeia', css_class='form-group col-md-3 mb-0'), Column('ativu', css_class='form-group col-md-2 mb-0'), css_class='form-row'))

	def clean(self):
		cleaned = super().clean()
		village, aldeia = cleaned.get('village'), cleaned.get('aldeia')
		if village and aldeia and aldeia.village_id != village.pk:
			self.add_error('aldeia', "Aldeia ne'e la hela iha suku ne'e.")
		return cleaned


class FiskaisUserField(forms.ModelChoiceField):
	def label_from_instance(self, obj):
		return f'{obj.get_full_name() or obj.get_username()} ({obj.get_username()})'


class FiskaisForm(forms.ModelForm):
	user = FiskaisUserField(label="Fiskais", queryset=User.objects.none())

	class Meta:
		model = FiskaisTempat
		fields = ['user', 'tempat']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# hanya akun berperan Fiskais yang aktif dan belum ditugaskan
		self.fields['user'].queryset = User.objects.filter(
			groups__name=roles.FISKAIS, is_active=True, fiskais_tempat__isnull=True).order_by('username')
		self.fields['tempat'].queryset = TempatVoting.objects.filter(ativu=True).select_related('village')
		self.helper = _helper(Row(Column('user', css_class='form-group col-md-6 mb-0'), Column('tempat', css_class='form-group col-md-6 mb-0'), css_class='form-row'))


class ResultadoForm(forms.ModelForm):
	class Meta:
		model = Resultado
		fields = ['votos_partidu', 'votos_total', 'foto', 'formulariu', 'obs']
		widgets = {'obs': forms.Textarea(attrs={'rows': 2})}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['foto'].required = True
		self.fields['formulariu'].required = True
		# FileInput biasa: tanpa tautan/URL ke file tersimpan (penyimpanan privat)
		self.fields['foto'].widget = forms.FileInput(attrs={'accept': 'image/jpeg,image/png'})
		self.fields['formulariu'].widget = forms.FileInput(attrs={'accept': 'application/pdf'})
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.layout = Layout(
			Row(Column('votos_partidu', css_class='form-group col-md-6 mb-0'), Column('votos_total', css_class='form-group col-md-6 mb-0'), css_class='form-row'),
			Row(Column('foto', css_class='form-group col-md-6 mb-0'), Column('formulariu', css_class='form-group col-md-6 mb-0'), css_class='form-row'),
			'obs',
			HTML('<button class="btn btn-sm btn-primary" type="submit" title="Submete">Submete Rezultadu <i class="fa fa-check"></i></button>'))

	def clean_foto(self):
		f = self.cleaned_data.get('foto')
		if f and isinstance(f, UploadedFile):
			# periksa file asli dulu; lalu dekode ulang agar EXIF dan data tambahan terbuang
			validate_image_size(f)
			validate_image_content(f)
			return sanitize_image(f)
		return f

	def clean_formulariu(self):
		f = self.cleaned_data.get('formulariu')
		if f and isinstance(f, UploadedFile):
			validate_pdf_size(f)
			validate_pdf_content(f)
		return f

	def clean(self):
		cleaned = super().clean()
		partidu, total = cleaned.get('votos_partidu'), cleaned.get('votos_total')
		if partidu is not None and total is not None and partidu > total:
			self.add_error('votos_partidu', 'Votu PD la bele boot liu total votu iha tempat.')
		return cleaned
