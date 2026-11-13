import datetime
import io
from xml.sax.saxutils import escape
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from custom.models import Village
from membro.delegadu import delegadu_data
from membro.utils import log_historia
from users.utils import c_user_emp

TITLE = 'LISTA DELEGADO/A ALDEIA {n} IHA SUKU {suku}, TUIR KONFERÉNSIA'
TITLE_HOTU = 'LISTA DELEGADO/A IHA SUKU {n_suku} NO ALDEIA {n_aldeia}, TUIR KONFERÉNSIA'
SUBTITLE = 'POSTU ADMINISTRATIVU {postu}'


def _village_or_404(request, pk):
	"""Peran suku hanya boleh membuka sukunya sendiri."""
	village = get_object_or_404(Village, pk=pk)
	group = c_user_group(request.user)
	if group in roles.SUKU_ROLES:
		e = c_user_emp(request.user)
		if not e or e.village_id != village.pk:
			raise Http404
	return village


def _title(data):
	return TITLE.format(n=data['n_aldeia'], suku=data['village'].name.upper()), SUBTITLE.format(postu=settings.PD_POSTU.upper())


def _all_data():
	"""Data delegadu semua suku + total, untuk halaman dan PDF 'Suku Hotu'."""
	datas = [delegadu_data(v) for v in Village.objects.all()]
	totais = {'suku': len(datas), 'aldeia': sum(d['n_aldeia'] for d in datas), 'delegadu': sum(d['n_delegadu'] for d in datas)}
	return datas, totais


def _title_hotu(totais):
	return (TITLE_HOTU.format(n_suku=totais['suku'], n_aldeia=totais['aldeia']), SUBTITLE.format(postu=settings.PD_POSTU.upper()))


def _letterhead():
	return {'nama': settings.PD_NAMA_SEKRETARIADO, 'postu': settings.PD_POSTU, 'alamat': settings.PD_ALAMAT, 'kontaktu': settings.PD_KONTAKTU}


@login_required
@allowed_users(allowed_roles=roles.DELEGADU_ROLES)
def DelegaduIndex(request):
	"""Peran suku langsung ke sukunya; Postu memilih suku atau membuka semua suku sekaligus."""
	group = c_user_group(request.user)
	if group in roles.SUKU_ROLES:
		e = c_user_emp(request.user)
		if e and e.village_id:
			return redirect('membro-delegadu', e.village_id)
		raise Http404
	context = {'group': group, 'villages': Village.objects.all(), 'can_hotu': group in roles.DELEGADU_HOTU_ROLES,
		'title': 'Lista Delegadu', 'legend': 'Lista Delegadu'}
	return render(request, 'membro/delegadu_index.html', context)


@login_required
@allowed_users(allowed_roles=roles.DELEGADU_ROLES)
def DelegaduSuku(request, pk):
	group = c_user_group(request.user)
	village = _village_or_404(request, pk)
	data = delegadu_data(village)
	title, subtitle = _title(data)
	context = {
		'group': group, 'data': data, 'village': village, 'doc_title': title, 'doc_subtitle': subtitle, 'letterhead': _letterhead(),
		'can_index': group not in roles.SUKU_ROLES, 'can_hotu': group in roles.DELEGADU_HOTU_ROLES,
		'title': f'Delegadu Suku {village.name}', 'legend': f'Delegadu Suku {village.name}',
		'meta_description': f'Lista delegadu suku {village.name}, Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'membro/delegadu.html', context)


@login_required
@allowed_users(allowed_roles=roles.DELEGADU_HOTU_ROLES)
def DelegaduHotu(request):
	"""Delegadu semua suku dalam satu dokumen (tiap suku satu halaman saat dicetak)."""
	datas, totais = _all_data()
	title, subtitle = _title_hotu(totais)
	context = {
		'group': c_user_group(request.user), 'datas': datas, 'totais': totais, 'doc_title': title, 'doc_subtitle': subtitle,
		'letterhead': _letterhead(), 'title': 'Delegadu Suku Hotu', 'legend': 'Delegadu Suku Hotu',
		'meta_description': 'Lista delegadu semua suku, Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'membro/delegadu_hotu.html', context)


def build_pdf(datas, totais=None):
	"""PDF A4 mirip dokumen resmi: kop surat, judul, tabel Naran | Pozisaun | Aldeia | Nu. Kartaun Eleitoral | Nu. HP WA.
	Satu suku: `datas` berisi satu data. Semua suku: `totais` diisi dan tiap suku mulai di halaman baru."""
	from reportlab.lib import colors
	from reportlab.lib.pagesizes import A4
	from reportlab.lib.styles import ParagraphStyle
	from reportlab.lib.units import mm
	from reportlab.platypus import HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

	semua = totais is not None
	base = ParagraphStyle('base', fontName='Times-Roman', fontSize=9.5, leading=11.5)
	bold = ParagraphStyle('bold', parent=base, fontName='Times-Bold')
	head = ParagraphStyle('head', parent=bold, alignment=1)
	center = ParagraphStyle('center', parent=base, alignment=1)
	center_b = ParagraphStyle('center_b', parent=bold, alignment=1)
	lh_b = ParagraphStyle('lh_b', fontName='Times-Bold', fontSize=13, leading=16)
	lh = ParagraphStyle('lh', fontName='Times-Bold', fontSize=10.5, leading=13)
	ttl = ParagraphStyle('ttl', fontName='Courier-Bold', fontSize=10, leading=13, alignment=1)
	suku_h = ParagraphStyle('suku_h', fontName='Times-Bold', fontSize=12, leading=15, spaceAfter=4)

	def p(text, style):
		return Paragraph(escape(text or ''), style)

	def tabel(data):
		header = [p('NARAN KOMPLETU', head), p('POZISAUN', head), p('ALDEIA', head), p('NÚ. KARTAUN ELEITORAL', head), p('NÚ HP WA', head)]
		rows, styles, heights = [header], [], [None]
		spacer = ['', '', '', '', '']

		def person(r):
			return [p(r['nome'], bold if r['utama'] else base), p(r['pozisaun'], bold if r['utama'] else base), '', p(r['eleitoral'], center), '']

		for r in data['suku_rows']:
			rows.append([p(r['nome'], bold if r['utama'] else base), p(r['pozisaun'], bold if r['utama'] else base),
				p(r['aldeia'], center), p(r['eleitoral'], center), p(r['hp'], center)])
			heights.append(None)
		if data['suku_rows']:
			rows.append(spacer); heights.append(3 * mm)
		for blk in data['blocks']:
			start = len(rows)
			for r in (blk['rows'] or [None]):
				rows.append([p('Seidauk iha delegadu', base), '', '', '', ''] if r is None else person(r))
				heights.append(None)
			end = len(rows) - 1
			rows[start][2] = p(blk['aldeia'], center_b)
			rows[start][4] = p(blk['hp'], center)
			if end > start:
				styles += [('SPAN', (2, start), (2, end)), ('SPAN', (4, start), (4, end))]
			rows.append(spacer); heights.append(3 * mm)
		t = Table(rows, colWidths=[58 * mm, 38 * mm, 30 * mm, 30 * mm, 24 * mm], rowHeights=heights, repeatRows=1)
		t.setStyle(TableStyle([
			('BOX', (0, 0), (-1, -1), 0.7, colors.black), ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
			('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
			('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
		] + styles))
		for i, h in enumerate(heights):  # baris pemisah antar blok tanpa garis dalam
			if h is not None and i > 0:
				t.setStyle(TableStyle([('LINEBELOW', (0, i), (-1, i), 0.4, colors.black), ('TOPPADDING', (0, i), (-1, i), 0), ('BOTTOMPADDING', (0, i), (-1, i), 0)]))
		return t

	nome = 'Suku Hotu' if semua else f'Suku {datas[0]["village"].name}'
	buf = io.BytesIO()
	doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=16 * mm,
		title=f'Lista Delegadu {nome}', author=settings.PD_NAMA_SEKRETARIADO)
	story = []
	flag = settings.BASE_DIR / 'main' / 'static' / 'main' / 'images' / 'bandeira_pd.png'
	lokasi = f'Postu {settings.PD_POSTU}, Dili-Timor Leste' if semua else f'Postu {settings.PD_POSTU}, Suco {datas[0]["village"].name}, Dili-Timor Leste'
	letter = [p(settings.PD_NAMA_SEKRETARIADO, lh_b), p(lokasi, lh), p(f'Rua : {settings.PD_ALAMAT}', lh), p(f'Mobile : {settings.PD_KONTAKTU}', lh)]
	kop = Table([[Image(str(flag), width=40 * mm, height=40 * mm * 337 / 592), letter]], colWidths=[46 * mm, 134 * mm])
	kop.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
	story += [kop, Spacer(1, 2 * mm), HRFlowable(width='100%', thickness=0.8, color=colors.black), Spacer(1, 3 * mm)]
	title, subtitle = _title_hotu(totais) if semua else _title(datas[0])
	story += [Paragraph(escape(title), ttl), Paragraph(escape(subtitle), ttl), Spacer(1, 4 * mm)]
	for i, data in enumerate(datas):
		if semua:
			if i:
				story.append(PageBreak())
			story.append(Paragraph(escape(f'SUKU {data["village"].name.upper()} · {data["n_aldeia"]} aldeia · {data["n_delegadu"]} delegadu'), suku_h))
		story.append(tabel(data))

	stamp = datetime.date.today().strftime('%d/%m/%Y')

	def footer(canvas, document):
		canvas.saveState()
		canvas.setFont('Times-Roman', 8)
		canvas.drawString(15 * mm, 9 * mm, f'SGDM-PDPADA · {nome} · Imprime iha {stamp}')
		canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f'Pajina {document.page}')
		canvas.restoreState()

	doc.build(story, onFirstPage=footer, onLaterPages=footer)
	return buf.getvalue()


def _pdf_response(pdf, nome_file):
	response = HttpResponse(pdf, content_type='application/pdf')
	response['Content-Disposition'] = f'inline; filename="{nome_file}-{datetime.date.today():%Y%m%d}.pdf"'
	response['Cache-Control'] = 'private, no-store'
	response['X-Content-Type-Options'] = 'nosniff'
	return response


@login_required
@allowed_users(allowed_roles=roles.DELEGADU_ROLES)
def DelegaduPdf(request, pk):
	village = _village_or_404(request, pk)
	pdf = build_pdf([delegadu_data(village)])
	log_historia(request.user, None, 'Ekspor', f'Lista Delegadu PDF · Suku {village.name}', nome='Ekspor PDF')
	return _pdf_response(pdf, f'delegadu-suku-{village.pk}')


@login_required
@allowed_users(allowed_roles=roles.DELEGADU_HOTU_ROLES)
def DelegaduHotuPdf(request):
	datas, totais = _all_data()
	pdf = build_pdf(datas, totais)
	log_historia(request.user, None, 'Ekspor', f'Lista Delegadu PDF · Suku Hotu ({totais["suku"]} suku, {totais["delegadu"]} delegadu)', nome='Ekspor PDF')
	return _pdf_response(pdf, 'delegadu-suku-hotu')
