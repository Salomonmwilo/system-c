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
from django.utils import dateformat, timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from . import audit
from .forms import LoginForm, MemberCreateForm, MemberRolesForm, ThresholdsForm
from .middleware import SESSION_KEY
from .models import AuditLog, Membership, OrganizationSettings, Role, User
from .charts import line_chart
from .dashboard import PERIODS, cumulative, period_days
from .permissions import OrgPermissionRequiredMixin, request_has_perm
from .registry import audit_action, dashboard_sections, search

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


# Journal : les connexions et déconnexions ne sont pas de l'« activité » à montrer.
QUIET_ACTIONS = frozenset({"login", "logout", "login_throttled", "test_action"})
ACTIVITY_TAGS = {
    "new": pgettext_lazy("activity", "New"),
    "done": pgettext_lazy("activity", "Done"),
    "config": pgettext_lazy("activity", "Config"),
    "change": pgettext_lazy("activity", "Changed"),
    "payment": pgettext_lazy("activity", "Payment"),
    "access": pgettext_lazy("activity", "Access"),
}


def recent_activity(request, limit: int = 5) -> list[dict]:
    entries = (
        AuditLog.objects.filter(organization=request.organization)
        .exclude(action__in=QUIET_ACTIONS)
        .select_related("actor")[:limit]
    )
    activity = []
    for entry in entries:
        label, tag = audit_action(entry.action)
        activity.append({
            "when": entry.created_at,
            "label": label or entry.action,
            "actor": entry.actor,
            "tag": tag,
            "tag_label": ACTIVITY_TAGS.get(tag, ACTIVITY_TAGS["change"]),
        })
    return activity


def overview_chart(sections, period: int):
    series = sorted((s for section in sections for s in section.get("series", [])), key=lambda s: s["rank"])
    if not series:
        return None
    days = period_days(timezone.localdate(), period)
    return line_chart(
        labels=[dateformat.format(day, "j b") for day in days],
        tips=[dateformat.format(day, "j F Y") for day in days],
        series=[{"label": s["label"], "values": cumulative(s["dates"], days)} for s in series],
    )


class DashboardView(OrgPermissionRequiredMixin, TemplateView):
    permission_required = "core.view_dashboard"
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        sections = dashboard_sections(request)
        priorities = [item for section in sections for item in section.get("priorities", [])]
        # Registre « À traiter » : seulement ce qui demande une action, par ordre d'urgence.
        priorities.sort(key=lambda item: (not item.get("urgent"), item["rank"]))
        try:
            period = int(request.GET.get("period", PERIODS[0]))
        except ValueError:
            period = PERIODS[0]
        if period not in PERIODS:
            period = PERIODS[0]
        context.update({
            "sections": sections,
            "priorities": [item for item in priorities if item["count"]],
            "pending_total": sum(item["count"] for item in priorities),
            "kpis": sorted((k for s in sections for k in s.get("kpis", [])), key=lambda k: k["rank"]),
            "cards": sorted((s["card"] for s in sections if s.get("card")), key=lambda c: c["order"]),
            "shortcuts": sorted((c for s in sections for c in s.get("shortcuts", [])), key=lambda c: c["order"]),
            "chart": overview_chart(sections, period),
            "period": period,
            "periods": PERIODS,
            "activity": recent_activity(request) if request_has_perm(request, "core.view_audit") else None,
            "today": timezone.localdate(),
        })
        if request_has_perm(request, "core.view_audit"):
            context["shortcuts"].append({"order": 90, "icon": "bar-chart", "label": _("See the audit log"),
                                         "url": reverse("core:audit")})
        context["shortcuts"] = context["shortcuts"][:4]
        return context


class SearchView(OrgPermissionRequiredMixin, View):
    """Recherche globale : chaque module filtre par organisation et par ses propres permissions."""

    permission_required = "core.search"
    MIN_LENGTH = 2

    def get(self, request):
        query = request.GET.get("q", "").strip()[:100]
        groups = search(request, query) if len(query) >= self.MIN_LENGTH else []
        return render(request, "core/search.html", {
            "query": query,
            "too_short": 0 < len(query) < self.MIN_LENGTH,
            "groups": [g for g in groups if g["results"]],
            "min_length": self.MIN_LENGTH,
        })


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

