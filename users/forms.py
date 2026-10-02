from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from config import roles as R
from custom.models import AdministrativePost, Aldeia, Village
from membro.models import Membru, Organizasaun
from users.models import SCOPE_FIELD_BY_ROLE, validate_scope

SCOPE_FIELDS = ('postu', 'village', 'aldeia', 'organizasaun')


class UserForm(forms.Form):
    username = forms.CharField(label='Username', max_length=150)
    first_name = forms.CharField(label='Naran', max_length=150)
    last_name = forms.CharField(label='Apelidu', max_length=150, required=False)
    email = forms.EmailField(label='Email', required=False)
    role = forms.ChoiceField(label='Papel (Grupu)', choices=R.ROLE_CHOICES)
    postu = forms.ModelChoiceField(AdministrativePost.objects.select_related('municipality'), required=False,
                                   label='Postu')
    village = forms.ModelChoiceField(Village.objects.select_related('administrativepost'), required=False,
                                     label='Suku')
    aldeia = forms.ModelChoiceField(Aldeia.objects.select_related('village'), required=False, label='Aldeia')
    organizasaun = forms.ModelChoiceField(Organizasaun.objects.all(), required=False, label='Organizasaun')
    membru = forms.ModelChoiceField(Membru.objects.select_related('aldeia__village'), required=False,
                                    label='Liga ba membru (opsionál)')

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance is not None:
            self.fields['username'].disabled = True

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        qs = User.objects.filter(username__iexact=username)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Username ne’e iha ona.')
        return username

    def clean(self):
        data = super().clean()
        role = data.get('role')
        if not role:
            return data
        validate_scope(role, data)
        keep = SCOPE_FIELD_BY_ROLE.get(role)
        for f in SCOPE_FIELDS:  # hamoos eskopu ne'ebé la relevante ba papel
            if f != keep:
                data[f] = None
        return data


class ChangePasswordForm(PasswordChangeForm):
    pass
