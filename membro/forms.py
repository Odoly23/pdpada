import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.core.files.uploadedfile import UploadedFile
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML
from django.urls import reverse
from custom.models import Village, Aldeia, Organizasaun, Municipality
from config import roles
from config.file_utils import sanitize_image, validate_image_content
from config.upload_utils import validate_image_size
from config.user_utils import c_user_group, c_user_scope
from membro.models import Membro, Alokasaun, OrgPozisaun, OrgResponsavel, Servisu, KATEGORIA, POZISAUN_POR_NIVEL

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
	# Servisu agora (disimpan iha model Servisu): form servisu tuir status
	_PILIH = [('', '--- Hili ---')]
	sv_status = forms.ChoiceField(label="Servisu agora", choices=_PILIH + Servisu.STATUS)
	sv_setor = forms.ChoiceField(label="Tipu Instituisaun", choices=_PILIH + Servisu.SETOR, required=False)
	sv_tipu = forms.ChoiceField(label="Tipu Servisu", choices=_PILIH + Servisu.TIPU_LAOS, required=False)
	sv_instituisaun = forms.CharField(label="Instituisaun / Kompañia", max_length=150, required=False)
	sv_diresaun = forms.CharField(label="Diresaun / Departamentu", max_length=120, required=False)
	sv_pozisaun = forms.CharField(label="Pozisaun / Kargu", max_length=100, required=False)
	sv_kategoria = forms.CharField(label="Kategoria", max_length=50, required=False)
	sv_grau = forms.CharField(label="Grau", max_length=20, required=False)
	sv_data_hahu = forms.DateField(label="Data Hahu Servisu", widget=DateInput(), required=False)
	sv_municipality = forms.ModelChoiceField(label="Municipiu Servisu", queryset=Municipality.objects.all(), required=False)
	sv_atividade = forms.ChoiceField(label="Ita halo saida agora?", choices=_PILIH + Servisu.ATIVIDADE, required=False)
	sv_detalle = forms.CharField(label="Detalle (ezemplu: eskola, fatin, atividade)", max_length=200, required=False)

	class Meta:
		model = Membro
		fields = ['kategoria', 'nome', 'sex', 'place_of_birth', 'date_of_birth', 'marital', 'nu_eleitoral',
			'telefone', 'image', 'file_eleitoral', 'village', 'aldeia', 'address', 'organizasaun', 'data_hakbit', 'status']

	def __init__(self, *args, user=None, **kwargs):
		super().__init__(*args, **kwargs)
		group = c_user_group(user) if user else None
		scope = c_user_scope(user) if user else None
		self.fields['organizasaun'].queryset = Organizasaun.objects.filter(is_active=True)
		self.fields['organizasaun'].empty_label = '--- Laiha ---'
		self.fields['kategoria'].initial = 'Militante'
		self.fields['kategoria'].help_text = 'Militante: membru ho Nu. Eleitoral. Simpatizante: dadus simples (Nu. Eleitoral opsionál).'
		self.fields['nu_eleitoral'].help_text = 'Obrigatóriu ba Militante; Simpatizante bele husik mamuk.'
		sv = Servisu.objects.filter(membro=self.instance).first() if self.instance.pk else None
		if sv:
			self.initial.update({'sv_status': sv.status, 'sv_setor': sv.setor or '', 'sv_tipu': sv.tipu_laos or '', 'sv_instituisaun': sv.instituisaun,
				'sv_diresaun': sv.diresaun, 'sv_pozisaun': sv.pozisaun, 'sv_kategoria': sv.kategoria, 'sv_grau': sv.grau, 'sv_data_hahu': sv.data_hahu,
				'sv_municipality': sv.municipality_id, 'sv_atividade': sv.atividade or '', 'sv_detalle': sv.detalle})
		# upload: FileInput biasa (tanpa tautan/URL publik); isi file diperiksa di server
		self.fields['image'].widget = forms.FileInput(attrs={'accept': 'image/jpeg,image/png'})
		self.fields['file_eleitoral'].widget = forms.FileInput(attrs={'accept': 'application/pdf'})
		self.fields['image'].error_messages['invalid_image'] = "Fotu la válidu: ficheiru ne'e la'ós imajen JPEG ka PNG ne'ebé loos."
		self.fields['image'].error_messages['invalid'] = "Fotu la válidu."
		has_img = bool(self.instance.pk and self.instance.image)
		has_pdf = bool(self.instance.pk and self.instance.file_eleitoral)
		self.fields['image'].help_text = 'JPEG/PNG, maksimu 2 MB.' + (' Fotu iha ona; upload foun atu troka.' if has_img else '')
		self.fields['file_eleitoral'].help_text = 'PDF deit, maksimu 5 MB.' + (' PDF iha ona; upload foun atu troka.' if has_pdf else '')
		self.fields['village'].queryset = Village.objects.all()
		self.fields['aldeia'].queryset = Aldeia.objects.select_related('village')
		if group == roles.SEKR_SUKU and scope and scope.village_id:
			self.fields['village'].queryset = Village.objects.filter(pk=scope.village_id)
			self.fields['aldeia'].queryset = Aldeia.objects.filter(village_id=scope.village_id)
			self.fields['village'].initial = scope.village_id
			self.fields['village'].disabled = True
		elif group == roles.SEKR_ORG and scope and scope.organizasaun_id:
			# anggota organisasi bisa berasal dari suku/aldeia mana pun di Postu; organisasi terkunci
			self.fields['organizasaun'].queryset = Organizasaun.objects.filter(pk=scope.organizasaun_id)
			self.fields['organizasaun'].empty_label = None
			self.fields['organizasaun'].initial = scope.organizasaun_id
			self.fields['organizasaun'].disabled = True
			village_id = self.data.get('village') if self.is_bound else (self.instance.village_id if self.instance.pk else None)
			valid = str(village_id).isdigit() if village_id else False
			self.fields['aldeia'].queryset = Aldeia.objects.filter(village_id=village_id) if valid else Aldeia.objects.none()
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
		self.helper.attrs = {'data-aldeias-url': reverse('ajax_load_aldeias')}  # dropdown Suku -> Aldeia
		self.helper.layout = Layout(
			Row(
				Column('kategoria', css_class='form-group col-md-3 mb-0'),
				Column('nome', css_class='form-group col-md-6 mb-0'),
				Column('sex', css_class='form-group col-md-3 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('nu_eleitoral', css_class='form-group col-md-4 mb-0'),
				Column('place_of_birth', css_class='form-group col-md-4 mb-0'),
				Column('date_of_birth', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('marital', css_class='form-group col-md-3 mb-0'),
				Column('telefone', css_class='form-group col-md-3 mb-0'),
				Column('image', css_class='form-group col-md-3 mb-0'),
				Column('file_eleitoral', css_class='form-group col-md-3 mb-0'),
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
			HTML('<hr><h6 class="text-primary">SERVISU</h6>'),
			Row(
				Column('sv_status', css_class='form-group col-md-4 mb-0'),
				Column('sv_setor', css_class='form-group col-md-4 mb-0 sv-kerja'),
				Column('sv_tipu', css_class='form-group col-md-4 mb-0 sv-laos'),
				css_class='form-row'
			),
			Row(
				Column('sv_instituisaun', css_class='form-group col-md-5 mb-0 sv-kerja'),
				Column('sv_diresaun', css_class='form-group col-md-4 mb-0 sv-governu'),
				Column('sv_pozisaun', css_class='form-group col-md-3 mb-0 sv-kerja'),
				css_class='form-row'
			),
			Row(
				Column('sv_kategoria', css_class='form-group col-md-3 mb-0 sv-governu'),
				Column('sv_grau', css_class='form-group col-md-3 mb-0 sv-governu'),
				Column('sv_data_hahu', css_class='form-group col-md-3 mb-0 sv-kerja'),
				Column('sv_municipality', css_class='form-group col-md-3 mb-0 sv-kerja'),
				css_class='form-row'
			),
			Row(
				Column('sv_atividade', css_class='form-group col-md-4 mb-0 sv-seidauk'),
				Column('sv_detalle', css_class='form-group col-md-8 mb-0 sv-seidauk'),
				css_class='form-row'
			),
			HTML(BTN_CANCEL),
			HTML(BTN_SAVE)
		)

	def clean_image(self):
		f = self.cleaned_data.get('image')
		if f and isinstance(f, UploadedFile):
			# periksa file ASLI dulu (ukuran, format JPEG/PNG, jumlah piksel); validator model baru
			# berjalan setelah foto dibersihkan sehingga tidak cukup
			validate_image_size(f)
			validate_image_content(f)
			return sanitize_image(f)  # dekode + encode ulang: buang EXIF dan data tambahan
		return f

	def clean_nome(self):
		return ' '.join(self.cleaned_data['nome'].split())

	def clean_date_of_birth(self):
		dob = self.cleaned_data['date_of_birth']
		if dob > datetime.date.today():
			raise ValidationError('Data moris la bele iha futuru.')
		return dob

	def clean_nu_eleitoral(self):
		valor = normalize_eleitoral(self.cleaned_data.get('nu_eleitoral'))
		if not valor:
			return None  # Simpatizante bele laiha; Militante diperiksa iha clean()
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
		if cleaned.get('kategoria') == 'Militante' and not cleaned.get('nu_eleitoral'):
			self.add_error('nu_eleitoral', 'Nu. Eleitoral obrigatóriu ba Militante.')
		status = cleaned.get('sv_status')
		if status == 'Servisu':
			for campo, msg in [('sv_setor', 'Hili instituisaun governu ka laos governu.'), ('sv_instituisaun', 'Hatama naran instituisaun ka kompañia.'),
					('sv_pozisaun', 'Hatama pozisaun ka kargu.')]:
				if not cleaned.get(campo):
					self.add_error(campo, msg)
			if cleaned.get('sv_setor') == 'Laos Governu' and not cleaned.get('sv_tipu'):
				self.add_error('sv_tipu', 'Hili tipu servisu.')
			if cleaned.get('sv_data_hahu') and cleaned['sv_data_hahu'] > datetime.date.today():
				self.add_error('sv_data_hahu', 'Data hahu servisu la bele iha futuru.')
		elif status == 'Seidauk' and not cleaned.get('sv_atividade'):
			self.add_error('sv_atividade', 'Hili ita halo saida agora.')
		return cleaned

	def save_servisu(self, membro):
		"""Rai servisu agora: se iha servisu rai dadus servisu; se seidauk rai atividade (campu seluk hamoos)."""
		cd = self.cleaned_data
		kerja = cd['sv_status'] == 'Servisu'
		governu = kerja and cd.get('sv_setor') == 'Governu'
		defaults = {
			'status': cd['sv_status'], 'setor': cd.get('sv_setor') if kerja else None,
			'tipu_laos': cd.get('sv_tipu') if kerja and not governu else None,
			'instituisaun': cd.get('sv_instituisaun', '') if kerja else '', 'diresaun': cd.get('sv_diresaun', '') if governu else '',
			'pozisaun': cd.get('sv_pozisaun', '') if kerja else '', 'kategoria': cd.get('sv_kategoria', '') if governu else '',
			'grau': cd.get('sv_grau', '') if governu else '', 'data_hahu': cd.get('sv_data_hahu') if kerja else None,
			'municipality': cd.get('sv_municipality') if kerja else None,
			'atividade': cd.get('sv_atividade') if not kerja else None, 'detalle': cd.get('sv_detalle', '') if not kerja else '',
		}
		Servisu.objects.update_or_create(membro=membro, defaults=defaults)


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
		nu = f' ({obj.nu_eleitoral})' if obj.nu_eleitoral else ''
		return f'{obj.nome}{nu} - {obj.village}/{obj.aldeia}'


class AlokasaunForm(forms.ModelForm):
	membro = MembroChoiceField(label="Membru", queryset=Membro.objects.none())
	data_hahu = forms.DateField(label="Data Hahu", widget=DateInput())
	data_termina = forms.DateField(label="Data Termina", widget=DateInput(), required=False)

	class Meta:
		model = Alokasaun
		fields = ['membro', 'nivel', 'pozisaun', 'village', 'aldeia', 'organizasaun', 'data_hahu', 'data_termina', 'ativu']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# membru yang sudah punya pozisaun ativu (is_colocado) tidak tampil; saat edit, pemegangnya sendiri tetap tampil
		bebas = Q(is_colocado=False)
		if self.instance.pk:
			bebas |= Q(pk=self.instance.membro_id)
		self.fields['membro'].queryset = Membro.objects.filter(bebas, aprovasaun='Aprovadu', status='Ativu').select_related('village', 'aldeia')
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
			aldeia = None  # organizasaun opsional = sayap (Koord OJD Suku, dst.)
			if not village:
				self.add_error('village', 'Suku tenke hili.')
			elif membro.village_id != village.pk:
				self.add_error('membro', 'Membru ne\'e la hela iha suku ne\'e.')
			elif org and membro.organizasaun_id != org.pk:
				self.add_error('membro', 'Membru ne\'e la tama organizasaun ne\'e.')
		elif nivel == 'Aldeia':  # organizasaun opsional = sayap (Koord OJD Aldeia, dst.)
			if not aldeia:
				self.add_error('aldeia', 'Aldeia tenke hili.')
			elif membro.aldeia_id != aldeia.pk:
				self.add_error('membro', 'Membru ne\'e la hela iha aldeia ne\'e.')
			elif org and membro.organizasaun_id != org.pk:
				self.add_error('membro', 'Membru ne\'e la tama organizasaun ne\'e.')
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
			self.add_error('data_termina', 'Data termina tenke hafoin data hahu.')
		if cleaned.get('ativu') == 'Sim' and not self.errors:
			lain = Alokasaun.objects.filter(membro=membro, ativu='Sim').exclude(pk=self.instance.pk or 0).first()
			if lain:
				raise ValidationError(f'{membro.nome} iha ona pozisaun ativu: {lain.pozisaun} {lain.nivel}. Termina uluk pozisaun ne\'e.')
			qs = Alokasaun.objects.filter(nivel=nivel, pozisaun=pozisaun, ativu='Sim')
			if nivel == 'Suku':
				qs = qs.filter(village=village, organizasaun=org)  # org kosong = pemimpin utama suku
			elif nivel == 'Aldeia':
				qs = qs.filter(aldeia=aldeia, organizasaun=org)
			elif nivel == 'Organizasaun':
				qs = qs.filter(organizasaun=org)
			if self.instance.pk:
				qs = qs.exclude(pk=self.instance.pk)
			atual = qs.select_related('membro').first()
			if atual:
				raise ValidationError(f'{pozisaun} {nivel} ativu iha ona: {atual.membro.nome}. Halo nia la ativu uluk.')
		return cleaned


def _descendants(pos):
	"""Semua turunan satu posisi (untuk mencegah siklus saat memilih induk)."""
	found, stack = set(), [pos.pk]
	while stack:
		for child in OrgPozisaun.objects.filter(parent_id=stack.pop()).values_list('pk', flat=True):
			if child not in found:
				found.add(child)
				stack.append(child)
	return found


class OrgPozisaunForm(forms.ModelForm):
	class Meta:
		model = OrgPozisaun
		fields = ['naran', 'parent', 'urutan', 'deskrisaun', 'obs', 'ativu']
		widgets = {'deskrisaun': forms.Textarea(attrs={'rows': 6}), 'obs': forms.Textarea(attrs={'rows': 2})}
		help_texts = {'deskrisaun': 'Satu baris = satu tarefa.', 'parent': 'Husi pozisaun ida ne\'ebé hamutuk iha organigrama (kosongu = leten liu).'}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		qs = OrgPozisaun.objects.all()
		if self.instance.pk:
			qs = qs.exclude(pk__in={self.instance.pk} | _descendants(self.instance))
		self.fields['parent'].queryset = qs
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.layout = Layout(
			Row(Column('naran', css_class='form-group col-md-8 mb-0'), Column('urutan', css_class='form-group col-md-4 mb-0'), css_class='form-row'),
			Row(Column('parent', css_class='form-group col-md-8 mb-0'), Column('ativu', css_class='form-group col-md-4 mb-0'), css_class='form-row'),
			'deskrisaun', 'obs', HTML(BTN_CANCEL), HTML(BTN_SAVE))


class OrgResponsavelForm(forms.ModelForm):
	membro = MembroChoiceField(label="Membru (opsional)", queryset=Membro.objects.none(), required=False)
	naran = forms.CharField(label="Naran", max_length=150, required=False, help_text='Kosongu se hili membru. Isi se la rejistu iha sistema.')

	class Meta:
		model = OrgResponsavel
		fields = ['membro', 'naran', 'kargu', 'urutan']
		help_texts = {'urutan': '1 = koordenador (letra bold).'}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['membro'].queryset = Membro.objects.filter(aprovasaun='Aprovadu', status='Ativu').select_related('village', 'aldeia')
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.layout = Layout(
			'membro', Row(Column('naran', css_class='form-group col-md-6 mb-0'), Column('kargu', css_class='form-group col-md-4 mb-0'),
				Column('urutan', css_class='form-group col-md-2 mb-0'), css_class='form-row'),
			HTML(BTN_CANCEL), HTML(BTN_SAVE))

	def clean(self):
		cleaned = super().clean()
		membro, naran = cleaned.get('membro'), (cleaned.get('naran') or '').strip()
		if membro and not naran:
			naran = membro.nome
		if not naran:
			self.add_error('naran', 'Hili membru ka isi naran.')
		cleaned['naran'] = naran
		return cleaned

