from custom.models import Year


def ano_ativu(request):
	return {'ano_ativu': Year.objects.filter(is_active=True).first()}
