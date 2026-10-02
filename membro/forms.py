from django import forms
from django.core.exceptions import ValidationError

from membro.models import Kargu, Membru


class BootstrapMixin:
    def _style(self):
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.CheckboxSelectMultiple):
                continue
            w.attrs['class'] = (w.attrs.get('class', '') + (' form-check-input' if isinstance(
                w, forms.CheckboxInput) else ' form-control')).strip()


class MembruForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Membru
        fields = ['nu_eleitoral', 'naran', 'fatin_moris', 'data_moris', 'sexu', 'estadu_civil', 'edukasaun',
                  'okupasaun', 'telemovel', 'email', 'enderesu', 'foto', 'organizasaun', 'aldeia']
        widgets = {
            'data_moris': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'organizasaun': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, lock_aldeia=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aldeia'].queryset = self.fields['aldeia'].queryset.select_related('village')
        if lock_aldeia:  # Coordenador Aldeia: aldeia sempre nia aldeia rasik
            del self.fields['aldeia']
        self._style()

    def clean_nu_eleitoral(self):
        nu = self.cleaned_data['nu_eleitoral'].strip().upper()
        qs = Membru.objects.filter(nu_eleitoral__iexact=nu)  # ActiveManager: la inklui hamoos ona
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Nu. Eleitoral ne’e rejistu ona.')
        return nu


class KarguForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Kargu
        fields = ['membru', 'tipu', 'nivel', 'postu', 'village', 'aldeia', 'data_hahu']
        widgets = {'data_hahu': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['membru'].queryset = Membru.objects.select_related('aldeia__village')
        self._style()
