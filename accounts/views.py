from django.contrib.auth.views import LoginView, LogoutView

from core.models import AuditLog

from .forms import LockoutAuthenticationForm


class StaffLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LockoutAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.record("login", user=form.get_user(), request=self.request)
        lang = form.get_user().preferred_language
        if lang:
            self.request.session["_language"] = lang
            response.set_cookie("django_language", lang)
        return response


class StaffLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            AuditLog.record("logout", user=request.user, request=request)
        return super().post(request, *args, **kwargs)
