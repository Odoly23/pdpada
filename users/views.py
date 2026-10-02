import secrets

from axes.utils import reset
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from config import roles as R
from config.audit import audit
from config.decorators import perm_required
from config.models import AuditLog
from config.scope import get_role, scope_label
from users.forms import ChangePasswordForm, UserForm
from users.models import Profile


def new_temp_password():
    """Password sementara aleatóriu (sekretu 16 karakter); user tenke troka bainhira login."""
    return secrets.token_urlsafe(12)


class PdpadaLoginView(LoginView):
    template_name = 'home/login.html'
    redirect_authenticated_user = True


@never_cache
def password_change(request):
    if not request.user.is_authenticated:
        return redirect('login')
    form = ChangePasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        Profile.objects.filter(user=user).update(must_change_password=False)
        audit(request, 'password_change', user.username)
        messages.success(request, 'Password troka ho susesu.')
        return redirect('home')
    return render(request, 'auth/change_password.html', {
        'form': form, 'legend': 'Troka Password',
        'forced': getattr(getattr(request.user, 'profile', None), 'must_change_password', False)})


def _role_of(user):
    return get_role(user)


@perm_required('users.manage_users')
def user_list(request):
    users = (User.objects.select_related('profile__postu', 'profile__village', 'profile__aldeia',
                                          'profile__organizasaun').prefetch_related('groups')
             .order_by('username'))
    rows = [{'user': u, 'role': R.ROLE_LABELS.get(_role_of(u), '-'), 'scope': scope_label(u)} for u in users]
    return render(request, 'users/list.html', {'rows': rows, 'legend': 'Jestaun User'})


def _initial(user):
    p = getattr(user, 'profile', None)
    return {
        'username': user.username, 'first_name': user.first_name, 'last_name': user.last_name,
        'email': user.email, 'role': _role_of(user),
        'postu': getattr(p, 'postu', None), 'village': getattr(p, 'village', None),
        'aldeia': getattr(p, 'aldeia', None), 'organizasaun': getattr(p, 'organizasaun', None),
        'membru': getattr(p, 'membru', None),
    }


def _apply(user, d):
    user.first_name, user.last_name, user.email = d['first_name'], d['last_name'], d['email']
    user.save()
    group = Group.objects.get(name=d['role'])
    user.groups.set([group])  # papel ida de'it ba user ida: determinístiku
    user._role = d['role']
    Profile.objects.update_or_create(user=user, defaults={
        'postu': d['postu'], 'village': d['village'], 'aldeia': d['aldeia'],
        'organizasaun': d['organizasaun'], 'membru': d['membru']})


def _show_password(request, user, password, reason):
    resp = render(request, 'users/temp_password.html', {
        'target': user, 'password': password, 'legend': 'Password Sementara', 'reason': reason})
    resp['Cache-Control'] = 'no-store'
    return resp


@perm_required('users.manage_users')
@transaction.atomic
def user_create(request):
    form = UserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        password = new_temp_password()
        user = User.objects.create_user(username=d['username'], password=password)
        _apply(user, d)
        Profile.objects.filter(user=user).update(must_change_password=True)
        audit(request, 'user_create', user.username, f'role={d["role"]}')
        return _show_password(request, user, password, 'User foun kria ona.')
    return render(request, 'users/form.html', {'form': form, 'legend': 'User Foun'})


@perm_required('users.manage_users')
@transaction.atomic
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, initial=_initial(user), instance=user)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        if user == request.user and d['role'] != _role_of(user):
            messages.error(request, 'Ita la bele troka papel rasik.')
        else:
            _apply(user, d)
            audit(request, 'user_edit', user.username, f'role={d["role"]}')
            messages.success(request, 'User atualiza ona.')
            return redirect('user-list')
    return render(request, 'users/form.html', {'form': form, 'legend': f'Edita {user.username}', 'edit': True})


@perm_required('users.manage_users')
@require_POST
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    password = new_temp_password()
    user.set_password(password)
    user.save()
    Profile.objects.filter(user=user).update(must_change_password=True)
    audit(request, 'password_reset', user.username)
    return _show_password(request, user, password, 'Password reset ona.')


@perm_required('users.manage_users')
@require_POST
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'Ita la bele deativa rasik.')
    else:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        audit(request, 'user_activate' if user.is_active else 'user_deactivate', user.username)
        messages.success(request, f'{user.username}: {"ativu" if user.is_active else "la ativu"}.')
    return redirect('user-list')


@perm_required('users.manage_users')
@require_POST
def user_unlock(request, pk):
    """Hamoos bloku axes (tentativa login barak) ba user ida."""
    user = get_object_or_404(User, pk=pk)
    reset(username=user.username)
    audit(request, 'user_unlock', user.username)
    messages.success(request, f'Bloku login {user.username} hamoos ona.')
    return redirect('user-list')


@perm_required('config.view_auditlog')
def audit_list(request):
    logs = AuditLog.objects.select_related('user')[:500]
    return render(request, 'users/audit.html', {'logs': logs, 'legend': 'Audit Log (500 ikus)'})
