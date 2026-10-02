import mimetypes

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from config import roles as R
from config.audit import audit
from config.decorators import perm_required
from config.scope import get_profile, get_role, kargu_queryset, membru_queryset
from membro.forms import KarguForm, MembruForm
from membro.models import Kargu, Membru


def _scoped_membru(request, public_id):
    """Objetu liu husi queryset eskopu → 404 se iha por for a (la hatudu existénsia)."""
    qs = membru_queryset(request.user).select_related('aldeia__village__administrativepost__municipality')
    return get_object_or_404(qs, public_id=public_id)


def _can_edit(user, membru):
    role = get_role(user)
    if role == R.ADMIN:
        return True
    return role == R.ALDEIA and not membru.is_locked


@perm_required('membro.view_membru')
def membru_list(request):
    qs = membru_queryset(request.user).select_related('aldeia__village').prefetch_related('organizasaun')
    estadu = request.GET.get('estadu')
    if estadu in Membru.Estadu.values:
        qs = qs.filter(estadu=estadu)
    return render(request, 'membro/list.html', {
        'membrus': qs, 'legend': 'Lista Membru', 'estadu': estadu, 'estadus': Membru.Estadu.choices})


@perm_required('membro.view_membru')
def membru_detail(request, public_id):
    m = _scoped_membru(request, public_id)
    return render(request, 'membro/detail.html', {
        'm': m, 'legend': m.naran, 'kargus': m.kargus.all(),
        'can_edit': _can_edit(request.user, m),
        'can_delete': request.user.has_perm('membro.delete_membru'),
        'can_confirm': request.user.has_perm('membro.confirm_membru') and m.estadu == Membru.Estadu.REJISTADU,
        'can_approve': request.user.has_perm('membro.approve_membru') and m.estadu == Membru.Estadu.KONFIRMADU,
    })


@perm_required('membro.add_membru')
def membru_create(request):
    profile = get_profile(request.user)
    if get_role(request.user) != R.ALDEIA or not profile or not profile.aldeia_id:
        raise PermissionDenied  # input membru = Coordenador Aldeia de'it
    form = MembruForm(request.POST or None, request.FILES or None, lock_aldeia=True)
    if request.method == 'POST' and form.is_valid():
        m = form.save(commit=False)
        m.aldeia, m.created_by = profile.aldeia, request.user
        m.save()
        form.save_m2m()
        audit(request, 'membru_create', m.public_id, m.naran)
        messages.success(request, 'Membru rejistu ona. Hein konfirmasaun Coordenador Suku.')
        return redirect('membru-detail', public_id=m.public_id)
    return render(request, 'membro/form.html', {'form': form, 'legend': 'Rejistu Membru Foun'})


@perm_required('membro.change_membru')
def membru_edit(request, public_id):
    m = _scoped_membru(request, public_id)
    if not _can_edit(request.user, m):
        raise PermissionDenied  # dadus konfirma ona = fechadu ba Aldeia
    form = MembruForm(request.POST or None, request.FILES or None, instance=m,
                      lock_aldeia=get_role(request.user) == R.ALDEIA)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        form.save_m2m()
        audit(request, 'membru_edit', m.public_id, m.naran)
        messages.success(request, 'Dadus membru atualiza ona.')
        return redirect('membru-detail', public_id=m.public_id)
    return render(request, 'membro/form.html', {'form': form, 'legend': f'Edita {m.naran}', 'm': m})


@perm_required('membro.delete_membru')
@require_POST
def membru_delete(request, public_id):
    m = _scoped_membru(request, public_id)
    m.soft_delete(request.user)
    audit(request, 'membru_delete', m.public_id, m.naran)
    messages.success(request, 'Membru hamoos ona (bele restaura husi admin database).')
    return redirect('membru-list')


@perm_required('membro.confirm_membru')
def pending_konfirma(request):
    qs = (membru_queryset(request.user).filter(estadu=Membru.Estadu.REJISTADU)
          .select_related('aldeia__village'))
    return render(request, 'membro/pending.html', {
        'membrus': qs, 'legend': 'Membru Hein Konfirmasaun (Suku)', 'action': 'konfirma'})


@perm_required('membro.approve_membru')
def pending_aprova(request):
    qs = (membru_queryset(request.user).filter(estadu=Membru.Estadu.KONFIRMADU)
          .select_related('aldeia__village'))
    return render(request, 'membro/pending.html', {
        'membrus': qs, 'legend': 'Membru Hein Aprovasaun (Postu)', 'action': 'aprova'})


@perm_required('membro.confirm_membru')
@require_POST
def membru_konfirma(request, public_id):
    m = _scoped_membru(request, public_id)
    try:
        m.konfirma(request.user)
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    else:
        audit(request, 'membru_konfirma', m.public_id, m.naran)
        messages.success(request, f'{m.naran} konfirma ona.')
    return redirect('pending-konfirma')


@perm_required('membro.approve_membru')
@require_POST
def membru_aprova(request, public_id):
    m = _scoped_membru(request, public_id)
    try:
        m.aprova(request.user)
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    else:
        audit(request, 'membru_aprova', m.public_id, m.naran)
        messages.success(request, f'{m.naran} aprova ona.')
    return redirect('pending-aprova')


@perm_required('membro.view_membru')
def membru_foto(request, public_id):
    """Foto sirvi de'it ba user ne'ebé iha eskopu (media la publiku)."""
    m = _scoped_membru(request, public_id)
    if not m.foto:
        raise Http404
    resp = FileResponse(m.foto.open('rb'), content_type=mimetypes.guess_type(m.foto.name)[0] or 'image/jpeg')
    resp['Cache-Control'] = 'private, max-age=300'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


# ── Kargu (Coordenador / Sekjen) ─────────────────────────────────────────────

@perm_required('membro.view_kargu')
def kargu_list(request):
    qs = kargu_queryset(request.user).filter(is_active=True)
    return render(request, 'membro/kargu_list.html', {
        'kargus': qs, 'legend': 'Coordenador & Sekjen',
        'can_add': request.user.has_perm('membro.add_kargu')})


@perm_required('membro.add_kargu')
def kargu_create(request):
    form = KarguForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        k = form.save(commit=False)
        k.created_by = request.user
        k.save()
        audit(request, 'kargu_create', k.pk, str(k))
        messages.success(request, 'Kargu rejistu ona.')
        return redirect('kargu-list')
    return render(request, 'membro/kargu_form.html', {'form': form, 'legend': 'Kargu Foun'})


@perm_required('membro.change_kargu')
@require_POST
def kargu_end(request, pk):
    k = get_object_or_404(Kargu, pk=pk, is_active=True)
    k.is_active, k.data_remata, k.updated_by = False, timezone.localdate(), request.user
    k.save()
    audit(request, 'kargu_end', k.pk, str(k))
    messages.success(request, 'Kargu remata ona.')
    return redirect('kargu-list')
