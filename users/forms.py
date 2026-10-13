from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML
from config import roles
from config.user_utils import c_user_group, c_user_scope
from custom.models import Village, Aldeia, Organizasaun
from users.models import UserScope

BTN_CANCEL = """ <a class="btn btn-secondary" href="{{ cancel_url }}" title="Cancela"><i class="fa fa-close"></i> Cancela</a> """
BTN_SAVE = """ <button class="btn btn-primary" type="submit" title="Rai"> Rai <i class="fa fa-save"></i></button> """


class UserForm(forms.ModelForm):
	group = forms.ChoiceField(label="Peran", choices=roles.ROLE_LABELS)
	village = forms.ModelChoiceField(label="Suku", queryset=Village.objects.all(), required=False)
	aldeia = forms.ModelChoiceField(label="Aldeia", queryset=Aldeia.objects.select_related('village'), required=False)
	organizasaun = forms.ModelChoiceField(label="Organizasaun", queryset=Organizasaun.objects.filter(is_active=True), required=False)
	password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), required=False)

	class Meta:
		model = User
		fields = ['username', 'first_name', 'email', 'is_active']
		labels = {'username': 'Username', 'first_name': 'Naran Kompletu', 'email': 'Email', 'is_active': 'Ativu'}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['first_name'].required = True
		if self.instance.pk:
			self.fields['group'].initial = c_user_group(self.instance)
			scope = c_user_scope(self.instance)
			if scope:
				self.fields['village'].initial = scope.village_id
				self.fields['aldeia'].initial = scope.aldeia_id
				self.fields['organizasaun'].initial = scope.organizasaun_id
			self.fields['password'].help_text = 'Husik mamuk atu la troka.'
		else:
			self.fields['password'].required = True
			self.fields['is_active'].initial = True
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.form_id = 'userForm'
		self.helper.attrs = {'data-aldeias-url': reverse('ajax_load_aldeias')}
		self.helper.layout = Layout(
			Row(
				Column('username', css_class='form-group col-md-4 mb-0'),
				Column('first_name', css_class='form-group col-md-4 mb-0'),
				Column('email', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('group', css_class='form-group col-md-4 mb-0'),
				Column('password', css_class='form-group col-md-4 mb-0'),
				Column('is_active', css_class='form-group col-md-4 mb-0'),
				css_class='form-row'
			),
			Row(
				Column('village', css_class='form-group col-md-4 mb-0 scope-village'),
				Column('aldeia', css_class='form-group col-md-4 mb-0 scope-aldeia'),
				Column('organizasaun', css_class='form-group col-md-4 mb-0 scope-organizasaun'),
				css_class='form-row'
			),
			HTML(BTN_CANCEL),
			HTML(BTN_SAVE)
		)

	def clean(self):
		cleaned = super().clean()
		group = cleaned.get('group')
		village, aldeia, org = cleaned.get('village'), cleaned.get('aldeia'), cleaned.get('organizasaun')
		if group in roles.SUKU_ROLES:
			if not village:
				self.add_error('village', 'Suku tenke hili ba peran ida ne\'e.')
			aldeia = org = None
		elif group in roles.ALDEIA_ROLES:
			if not aldeia:
				self.add_error('aldeia', 'Aldeia tenke hili ba peran ida ne\'e.')
			else:
				village = aldeia.village
			org = None
		elif group in roles.ORG_ROLES:
			if not org:
				self.add_error('organizasaun', 'Organizasaun tenke hili ba peran ida ne\'e.')
			village = aldeia = None
		else:
			village = aldeia = org = None
		cleaned['village'], cleaned['aldeia'], cleaned['organizasaun'] = village, aldeia, org
		password = cleaned.get('password')
		if password:
			try:
				validate_password(password, user=self.instance if self.instance.pk else User(username=cleaned.get('username', '')))
			except forms.ValidationError as e:
				self.add_error('password', e)
		return cleaned

	def save(self, commit=True):
		user = super().save(commit=False)
		if self.cleaned_data.get('password'):
			user.set_password(self.cleaned_data['password'])
		user.save()
		group, _ = Group.objects.get_or_create(name=self.cleaned_data['group'])
		user.groups.set([group])
		UserScope.objects.update_or_create(user=user, defaults={
			'village': self.cleaned_data['village'],
			'aldeia': self.cleaned_data['aldeia'],
			'organizasaun': self.cleaned_data['organizasaun'],
		})
		return user
