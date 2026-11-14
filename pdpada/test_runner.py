from django.conf import settings
from django.test.runner import DiscoverRunner


class TestRunner(DiscoverRunner):
	# Teste normál la presiza tiket formuláriu; teste middleware ativa fali ho override_settings.
	def setup_test_environment(self, **kwargs):
		super().setup_test_environment(**kwargs)
		settings.ONE_TIME_FORMS = False
