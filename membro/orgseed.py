"""Posisi organigrama komisaun sesuai dokumen resmi (kolom Pozisaun, Deskrisaun Tarefas, Obs.). Dipakai migrasi 0005."""

ROOT = 'Presidente Komisaun · Vice-Pres-1 · Vice-Pres-2'

POSISI = [
	(1, ROOT, None, [
		'Responsavel ba atividade realizasaun KPA-PADA',
		'Halo kordenasaun serviço ho seksaun sira sira hotu iha Komisaun nia laran',
		'Responsavel ba relatoriu ezekusaun orsamentu ba KPA-PADA.',
	], ''),
	(2, 'Tezoreira', ROOT, [
		"Toma nota ba orsamentu ne'ebé SIMU husi kontributor sira orsamentu ne'ebé simu husi Diresaun Finansas PD.",
		'Distribui orsamentu ba Seksaun sira hodi finansia atividade konferensia ho autorizasaun Presidente, V1 no V2',
		"Resposavel ba BINDEZ ruma ne'ebé uza ba realizasaun konferensia ho faktus no resibu original sira nudar prova ba gastus ho responsabilidade.",
		'Prepara relatoriu ezekusaun iha EXCEL no esplikasaun narativa.',
		'Anexa resimu, nota no faturas sira nudar prova ba gastus.',
	], 'Nota: Submete relatoriu detalha ba Presidente Komisaun tarde liu, loron 10 depois de konferensia.'),
	(3, 'Seksaun Verifikasaun Dadus', ROOT, [
		'Verifika ho kuidadu lista delegadu/konferensista sira husi Suco 7 no Aldeia 71.',
		'Halo klasifikasaun dadus bazeia ba Suco tuir kedas ho Aldeia Suco refere.',
		'Halo konfirmasaun ho Koordenador Suco no Aldeia ba lista delegadu molok konferensia hahú.',
		"Toma NOTA ba delegadu Suco no Aldeia ne'ebé la marka prezensa no relata kedas ba Koord. Suco no Aldeia refere.",
	], ''),
	(4, 'Seksaun Konsumu', ROOT, [
		'Responsavel ba Catering (han meiu-dia, snack no bee hemu) durante konferensia.',
		"Prepara hahan ho responsabilidade no garante hahan tasak diak no segoru ba ema hotu ne'ebé konsumu.",
		'Halo jestaun ba orsamentu konsumu nian no aprezenta nota gastus sira ba TEZOREIRA hodi prepara relatoriu.',
	], ''),
	(5, 'Seksaun Logistiku', ROOT, [
		"Responsavel ba fatin realizasaun konferensia inklui númeru kadeira ba Kuadru Nasional, Munisipiu no bainaka sira ne'ebé marka prezensa iha konferensia.",
		'Garante númeru kadeira sufisiente ba konferensista ka delegadu sira.',
		'Responsavel ba ekipamentu hodi apoiu realizasaun konferensia (sound-system, microphone, banner, sst).',
		'Rekolha no entrega resibu gastus aluga fatin no ekipamentu sira ba TEZOREIRA ligadu ho utilizasaun orsamentu.',
	], 'Nota: Submete resibu gastus sira ba Tezoreira loron 7 depois de konferensia.'),
	(6, 'Adm. no Notulensia Konferensia', ROOT, [
		'Resposavel ba NOTULEN konferensia.',
		"Toma NOTA ba pontus importante husi mensajen lideransa PD nian no expresaun spontaneaus husi bainaka sira ne'ebé marka prezensa iha konferensia.",
		"Prepara Notulen ho sekuensia anotasaun ne'ebé lojik hodi sai relatoriu konferensia nian.",
	], ''),
	(7, 'Seksaun Animasaun', ROOT, [
		'Responsavel ba animasaun durante konferensia.',
		"Responsavel ba atributu ka instrumentu sira ne'ebé impresta ka aluga husi belun sira.",
	], ''),
	(8, 'Seksaun Dekorasaun', ROOT, [
		"Prepara dekorasaun didiak ba meja konferensia no meja bainaka de honra nia túr fatin iha sala konferensia.",
	], ''),
	(9, 'Seksaun Preparasaun Atributu', ROOT, [
		'Dezenha Banner, Kartaun KPA no Logo iha Kamizola ba delegadu sira.',
		'Hamutuk ho Koord. No SekJen PADA responsavel ba atribuisaun atributu KPA-PADA ba delegadu no konferensista sira.',
	], ''),
	(10, 'Seksaun Dokumentasaun', ROOT, ['Responsavel ba kobertura konferensia (Foto + VDO)'], ''),
	(11, 'Mestre Ceremonia (MC)', ROOT, [
		"Jere konferensia TUIR DEIT sekuensia Agenda no Ordem ne'ebé prepara ona husi Komisaun Organizadora.",
		'MC labele halo improvizasaun no esplikasaun barak liu',
		'MC labele konkluzaun ba orador sira nia diskursu hodi hodi garente efisiensia tempu no efetividade konferensia.',
	], ''),
	(12, 'Ekipa Simu Bainaka', ROOT, [
		'Atende bainaka lori ba meja asina lista prezensa, hafoin akompanha ba túr fatin,',
		'Atende delegadu sira ba asina lista prezensa, simu atributu no akompanha ba túr fatin.',
		"Akompanha no koloka bainaka no delegadu sira tuir fatin ne'ebé prepara ona husi Komisaun Organizadora.",
	], ''),
]
