import re

from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings
from django.urls import reverse

from config.roles import SEKR_SUKU
from membro.models import Membro
from membro.tests import BaseCase


@override_settings(ONE_TIME_FORMS=True)
class OneTimeFormTests(BaseCase):
	# Middleware formuláriu uza dala ida: la rai dala rua no "Back" fó formuláriu foun.

	def token(self, html):
		return re.search(r'name="_ftoken" value="([^"]+)"', html).group(1)

	def get_form(self, url):
		resp = self.client.get(url)
		return resp, self.token(resp.content.decode())

	def data(self, token, nu='OT000001'):
		d = self.form_data(nu) if hasattr(self, 'form_data') else {}
		d['_ftoken'] = token
		return d

	def test_token_injected_and_page_not_cached(self):
		self.login('sekrsuku')
		resp, tok = self.get_form(reverse('membro-add'))
		self.assertTrue(tok)
		self.assertIn('no-store', resp['Cache-Control'])

	def test_each_render_gets_a_different_token(self):
		self.login('sekrsuku')
		_, t1 = self.get_form(reverse('membro-add'))
		_, t2 = self.get_form(reverse('membro-add'))
		self.assertNotEqual(t1, t2)

	def test_second_submit_of_same_form_is_blocked(self):
		self.login('sekrsuku')
		_, tok = self.get_form(reverse('membro-add'))
		first = self.client.post(reverse('membro-add'), self.data(tok, 'OT000002'))
		self.assertEqual(first.status_code, 302)
		self.assertEqual(Membro.objects.filter(nu_eleitoral='OT000002').count(), 1)
		again = self.client.post(reverse('membro-add'), self.data(tok, 'OT000003'))
		self.assertRedirects(again, reverse('membro-add'), fetch_redirect_response=False)
		self.assertFalse(Membro.objects.filter(nu_eleitoral='OT000003').exists())
		self.assertEqual(Membro.objects.count(), 1 + Membro.objects.exclude(nu_eleitoral='OT000002').count())
		page = self.client.get(reverse('membro-add'))
		self.assertContains(page, 'Formuláriu ne&#x27;e uza ona')

	def test_back_gives_fresh_blank_form_not_old_data(self):
		self.login('sekrsuku')
		_, tok = self.get_form(reverse('membro-add'))
		self.client.post(reverse('membro-add'), self.data(tok, 'OT000004'))
		resp, tok2 = self.get_form(reverse('membro-add'))
		self.assertNotContains(resp, 'OT000004')
		self.assertNotEqual(tok, tok2)

	def test_edit_form_after_save_shows_current_data(self):
		self.login('sekrsuku')
		m = self.make('OT000005')
		url = reverse('membro-update', args=[m.hashed])
		_, tok = self.get_form(url)
		d = self.data(tok, 'OT000005')
		d['nome'] = 'Naran Foun'
		self.client.post(url, d)
		resp = self.client.get(url)
		self.assertContains(resp, 'Naran Foun')

	def test_invalid_post_rerenders_form_with_new_token(self):
		self.login('sekrsuku')
		_, tok = self.get_form(reverse('membro-add'))
		d = self.data(tok)
		d['nome'] = ''
		resp = self.client.post(reverse('membro-add'), d)
		self.assertEqual(resp.status_code, 200)
		tok2 = self.token(resp.content.decode())
		self.assertNotEqual(tok, tok2)
		d['nome'] = 'Joao'
		d['_ftoken'] = tok2
		self.assertEqual(self.client.post(reverse('membro-add'), d).status_code, 302)

	def test_post_without_token_is_unaffected(self):
		self.login('sekrsuku')
		self.assertEqual(self.client.post(reverse('membro-add'), self.form_data('OT000006')).status_code, 302)

	def test_anonymous_pages_get_no_token(self):
		resp = self.client.get(reverse('login'))
		self.assertNotContains(resp, '_ftoken')

	def test_disabled_by_setting(self):
		self.login('sekrsuku')
		with override_settings(ONE_TIME_FORMS=False):
			self.assertNotContains(self.client.get(reverse('membro-add')), '_ftoken')

	def test_servisu_form_also_single_use(self):
		self.login('sekrsuku')
		m = self.make('OT000007')
		url = reverse('membro-servisu', args=[m.hashed])
		_, tok = self.get_form(url)
		p = {'status': 'Seidauk', 'atividade': 'Estudante', '_ftoken': tok}
		self.assertEqual(self.client.post(url, p).status_code, 302)
		p['atividade'] = 'Ajuda Uma'
		self.client.post(url, p)
		m.refresh_from_db()
		self.assertEqual(m.servisu.atividade, 'Estudante')
