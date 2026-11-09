from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from . import audit
from .forms import LoginForm, MemberCreateForm, MemberRolesForm, ThresholdsForm
from .middleware import SESSION_KEY
from .models import AuditLog, Membership, OrganizationSettings, Role, User
from .permissions import OrgPermissionRequiredMixin
from .registry import dashboard_sections

def _safe_next(request, fallback: str) -> str:
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return fallback


def _set_language_cookie(response, language: str) -> None:
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=365 * 24 * 60 * 60,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
    )


class LoginView(FormView):
    public = True
    template_name = "core/login.html"
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_invalid(self, form):
        if getattr(form, "throttled", False):
            audit.record("login_throttled")
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        response = HttpResponseRedirect(_safe_next(self.request, reverse("core:dashboard")))
        _set_language_cookie(response, user.preferred_language)
        return response


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("core:login")


logout_view.public = True


@require_POST
def switch_language(request):
    language = request.POST.get("language", "")
    if language not in dict(settings.LANGUAGES):
        language = settings.LANGUAGE_CODE
    if request.user.is_authenticated and request.user.preferred_language != language:
        request.user.preferred_language = language
        request.user.save(update_fields=["preferred_language"])
    response = HttpResponseRedirect(_safe_next(request, reverse("core:dashboard")))
    _set_language_cookie(response, language)
    return response


switch_language.public = True


@login_required
@require_POST
def switch_organization(request):
    wanted = request.POST.get("organization", "")
    if any(str(org.pk) == wanted for org in request.user_organizations):
        request.session[SESSION_KEY] = wanted
    return redirect("core:dashboard")


switch_organization.public = True  # ne donne accès qu'aux organisations dont on est membre


@login_required
def no_organization(request):
    return render(request, "core/no_organization.html", status=403)


no_organization.public = True


def permission_denied(request, exception=None):
    return render(request, "core/403.html", status=403)


def page_not_found(request, exception=None):
    return render(request, "core/404.html", status=404)


class DashboardView(OrgPermissionRequiredMixin, TemplateView):
    permission_required = "core.view_dashboard"
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sections"] = dashboard_sections(self.request)
        context["thresholds"] = OrganizationSettings.for_organization(self.request.organization)
        return context


class ProfilePasswordView(PasswordChangeView):
    public = True  # réservée à l'utilisateur connecté (login_required par PasswordChangeView)
    template_name = "core/password_change.html"
    success_url = reverse_lazy("core:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        audit.record("password_changed", actor=self.request.user, target=self.request.user)
        messages.success(self.request, _("Your password has been changed."))
        return response


class MemberListView(OrgPermissionRequiredMixin, TemplateView):
    permission_required = "core.manage_members"
    template_name = "core/members.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        memberships = (
            Membership.objects.filter(organization=self.request.organization)
            .select_related("user")
            .order_by("user__full_name", "role")
        )
        people: dict = {}
        labels = dict(Role.choices)
        for membership in memberships:
            entry = people.setdefault(membership.user_id, {"user": membership.user, "roles": []})
            entry["roles"].append(labels.get(membership.role, membership.role))
        context["people"] = list(people.values())
        return context


class MemberCreateView(OrgPermissionRequiredMixin, FormView):
    permission_required = "core.manage_members"
    template_name = "core/member_form.html"
    form_class = MemberCreateForm

    def form_valid(self, form):
        data = form.cleaned_data
        organization = self.request.organization
        with transaction.atomic():
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                full_name=data["full_name"],
                preferred_language=data["preferred_language"],
            )
            for role in data["roles"]:
                Membership.objects.create(user=user, organization=organization, role=role, created_by=self.request.user)
            audit.record(
                "member_created",
                actor=self.request.user,
                organization=organization,
                target=user,
                roles=sorted(data["roles"]),
            )
        messages.success(self.request, _("The account has been created."))
        return redirect("core:members")


class MemberRolesView(OrgPermissionRequiredMixin, FormView):
    permission_required = "core.manage_members"
    template_name = "core/member_roles.html"
    form_class = MemberRolesForm

    def dispatch(self, request, *args, **kwargs):
        self.member = None
        if request.user.is_authenticated and getattr(request, "organization", None) is not None:
            membership = (
                Membership.objects.filter(organization=request.organization, user_id=kwargs["user_id"])
                .select_related("user")
                .first()
            )
            if membership is None:
                return page_not_found(request)
            self.member = membership.user
        return super().dispatch(request, *args, **kwargs)

    def current_roles(self) -> set[str]:
        return set(
            Membership.objects.filter(organization=self.request.organization, user=self.member).values_list("role", flat=True)
        )

    def get_initial(self):
        return {"roles": sorted(self.current_roles())}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member"] = self.member
        return context

    def form_valid(self, form):
        organization = self.request.organization
        wanted = set(form.cleaned_data["roles"])
        current = self.current_roles()
        if self.member == self.request.user and Role.ORG_ADMIN in current and Role.ORG_ADMIN not in wanted:
            form.add_error("roles", _("You cannot remove your own organization administrator role."))
            return self.form_invalid(form)
        with transaction.atomic():
            Membership.objects.filter(organization=organization, user=self.member, role__in=current - wanted).delete()
            for role in wanted - current:
                Membership.objects.create(user=self.member, organization=organization, role=role, created_by=self.request.user)
            audit.record(
                "member_roles_changed",
                actor=self.request.user,
                organization=organization,
                target=self.member,
                added=sorted(wanted - current),
                removed=sorted(current - wanted),
            )
        messages.success(self.request, _("Roles have been updated."))
        return redirect("core:members")


class ThresholdsView(OrgPermissionRequiredMixin, FormView):
    permission_required = "core.manage_thresholds"
    template_name = "core/thresholds.html"
    form_class = ThresholdsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.settings_obj = OrganizationSettings.for_organization(self.request.organization)
        kwargs["instance"] = self.settings_obj
        return kwargs

    def form_valid(self, form):
        stored = OrganizationSettings.objects.get(pk=self.settings_obj.pk)  # le ModelForm a déjà modifié l'instance
        before = {name: getattr(stored, name) for name in form.fields}
        settings_obj = form.save(commit=False)
        settings_obj.updated_by = self.request.user
        settings_obj.save()
        after = {name: getattr(settings_obj, name) for name in form.fields}
        audit.record(
            "thresholds_changed",
            actor=self.request.user,
            organization=self.request.organization,
            target=settings_obj,
            **{f"{name}_before": before[name] for name in form.fields if before[name] != after[name]},
            **{f"{name}_after": after[name] for name in form.fields if before[name] != after[name]},
        )
        messages.success(self.request, _("Alert thresholds have been saved."))
        return redirect("core:thresholds")


class AuditLogView(OrgPermissionRequiredMixin, View):
    permission_required = "core.view_audit"

    def get(self, request):
        entries = AuditLog.objects.filter(organization=request.organization).select_related("actor")
        page = Paginator(entries, 50).get_page(request.GET.get("page"))
        return render(request, "core/audit.html", {"page": page})

