from django.db import migrations, models
import django.db.models.deletion


def isi_posisi(apps, schema_editor):
	"""Isi 12 posisi organigrama sesuai dokumen resmi (tanpa nama orang; responsavel diisi lewat sistem)."""
	from membro.orgseed import POSISI
	OrgPozisaun = apps.get_model('membro', 'OrgPozisaun')
	if OrgPozisaun.objects.exists():
		return
	made = {}
	for urutan, naran, parent, tarefas, obs in POSISI:
		made[naran] = OrgPozisaun.objects.create(
			naran=naran, parent=made.get(parent), urutan=urutan, deskrisaun='\n'.join(tarefas), obs=obs)


class Migration(migrations.Migration):

	dependencies = [
		('membro', '0004_membro_is_colocado'),
	]

	operations = [
		migrations.CreateModel(
			name='OrgPozisaun',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('naran', models.CharField(max_length=150, verbose_name='Pozisaun')),
				('urutan', models.PositiveSmallIntegerField(db_index=True, default=0, verbose_name='Nu. Urut')),
				('deskrisaun', models.TextField(blank=True, verbose_name='Deskrisaun Tarefas')),
				('obs', models.TextField(blank=True, verbose_name='Observasaun')),
				('ativu', models.BooleanField(default=True, verbose_name='Ativu')),
				('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sub', to='membro.orgpozisaun', verbose_name='Iha okos husi')),
			],
			options={'verbose_name': 'Pozisaun Organigrama', 'ordering': ['urutan', 'id']},
		),
		migrations.CreateModel(
			name='OrgResponsavel',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('naran', models.CharField(max_length=150, verbose_name='Naran')),
				('kargu', models.CharField(blank=True, max_length=80, verbose_name='Kargu')),
				('urutan', models.PositiveSmallIntegerField(default=1, verbose_name='Nu. Urut')),
				('membro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='membro.membro', verbose_name='Membru')),
				('pozisaun', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responsavel', to='membro.orgpozisaun')),
			],
			options={'verbose_name': 'Responsavel Organigrama', 'ordering': ['urutan', 'id']},
		),
		migrations.RunPython(isi_posisi, migrations.RunPython.noop),
	]
