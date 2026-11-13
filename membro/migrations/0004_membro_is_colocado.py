from django.db import migrations, models


def isi_is_colocado(apps, schema_editor):
	"""Membru yang sudah punya pozisaun ativu ditandai TRUE."""
	Membro, Alokasaun = apps.get_model('membro', 'Membro'), apps.get_model('membro', 'Alokasaun')
	ids = list(Alokasaun.objects.filter(ativu='Sim').values_list('membro_id', flat=True).distinct())
	Membro.objects.filter(pk__in=ids).update(is_colocado=True)


class Migration(migrations.Migration):

	dependencies = [
		('membro', '0003_alter_membro_hashed_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='membro',
			name='is_colocado',
			field=models.BooleanField(db_index=True, default=False, verbose_name='Iha Pozisaun'),
		),
		migrations.RunPython(isi_is_colocado, migrations.RunPython.noop),
	]
