from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views import View

from apps.core import audit
from apps.core.models import OrganizationSettings
from apps.core.permissions import OrgPermissionRequiredMixin, get_for_org, request_has_perm
from apps.partners.models import Affiliate

from . import services
from .forms import (
    BotFilterForm,
    BotUserCreateForm,
    BotUserForm,
    DeclareAppliedForm,
    ParameterDefinitionFormSet,
    RealDeclarationForm,
    ReasonForm,
    VersionForm,
)
from .models import (
    ApplicationDeclaration,
    BotUser,
    ConfigurationVersion,
    Override,
    ParameterDefinition,
    RobotType,
)


def _bot_user(request, pk) -> BotUser:
    return get_for_org(request, BotUser.objects.select_related("affiliate"), pk=pk)


def _version(request, pk) -> ConfigurationVersion:
    return get_for_org(request, ConfigurationVersion.objects.select_related("bot_user", "bot_user__affiliate"), pk=pk)


def _report(request, exc: Exception) -> None:
    if isinstance(exc, ValidationError):
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.error(request, str(exc) or _("You are not allowed to perform this action."))


def _available_affiliates(request):
    taken = BotUser.objects.filter(organization=request.organization).values("affiliate_id")
    return (
        Affiliate.objects.filter(organization=request.organization, archived_at__isnull=True)
        .exclude(id__in=taken)
        .order_by("display_name")
    )


class BotUserListView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.view_botuser"

    def get(self, request):
        form = BotFilterForm(request.GET or None)
        queryset = BotUser.objects.filter(organization=request.organization).select_related("affiliate")
        settings_obj = OrganizationSettings.for_organization(request.organization)
        if form.is_valid():
            data = form.cleaned_data
            if data["q"]:
                queryset = queryset.filter(affiliate__display_name__icontains=data["q"].strip())
            if data["status"]:
                queryset = queryset.filter(status=data["status"])
            if data["robot_type"]:
                queryset = queryset.filter(robot_type=data["robot_type"])
            if data["account_type"]:
                queryset = queryset.filter(current_account_type=data["account_type"])
            if data["alert"] == "to_apply":
                queryset = services.to_apply(queryset)
            elif data["alert"] in services.ALERTS:
                queryset = services.ALERTS[data["alert"]](queryset, settings_obj)
        page = Paginator(queryset.order_by("affiliate__display_name"), 25).get_page(request.GET.get("page"))
        return render(request, "bots/botuser_list.html", {"filter_form": form, "page": page})


class BotUserCreateView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.add_botuser"
    template_name = "bots/botuser_form.html"

    def get(self, request):
        initial = {}
        affiliate_id = request.GET.get("affiliate")
        affiliates = _available_affiliates(request)
        if affiliate_id and affiliates.filter(pk=affiliate_id).exists():
            initial["affiliate"] = affiliate_id
        form = BotUserCreateForm(initial=initial, affiliates=affiliates)
        return render(request, self.template_name, {"form": form, "creating": True})

    def post(self, request):
        form = BotUserCreateForm(request.POST, affiliates=_available_affiliates(request))
        if form.is_valid():
            data = form.cleaned_data
            try:
                bot_user = services.create_bot_user(
                    organization=request.organization, affiliate=data["affiliate"], actor=request.user, data=data
                )
            except (ValidationError, PermissionDenied) as exc:
                _report(request, exc)
            else:
                messages.success(request, _("The robot record has been created."))
                return redirect("bots:botuser_detail", pk=bot_user.pk)
        return render(request, self.template_name, {"form": form, "creating": True})


class BotUserUpdateView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.change_botuser"
    template_name = "bots/botuser_form.html"

    def get(self, request, pk):
        bot_user = _bot_user(request, pk)
        return render(request, self.template_name, {"form": BotUserForm(instance=bot_user), "bot_user": bot_user})

    def post(self, request, pk):
        bot_user = _bot_user(request, pk)
        snapshot = BotUser.objects.get(pk=bot_user.pk)
        form = BotUserForm(request.POST, instance=bot_user)
        if form.is_valid():
            try:
                services.update_bot_user(bot_user=snapshot, actor=request.user, data=form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, _("The robot record has been updated."))
                return redirect("bots:botuser_detail", pk=bot_user.pk)
        return render(request, self.template_name, {"form": form, "bot_user": snapshot})


class BotUserDetailView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.view_botuser"

    def get(self, request, pk):
        bot_user = _bot_user(request, pk)
        versions = bot_user.versions.select_related("created_by", "validated_by", "real_confirmed_by").prefetch_related(
            "parameters", "declarations__recorded_by", "declarations__correction"
        )
        latest = services.latest_validated(bot_user)
        applied = services.effective_applied(bot_user).select_related("version").order_by("-recorded_at").first()
        context = {
            "bot_user": bot_user,
            "affiliate": bot_user.affiliate,
            "versions": versions,
            "latest": latest,
            "draft": services.current_draft(bot_user),
            "applied_declaration": applied,
            "status_events": bot_user.status_events.select_related("actor")[:30],
            "can_view_affiliate": request_has_perm(request, "partners.view_affiliate"),
            "reason_form": ReasonForm(),
            "declare_form": DeclareAppliedForm(),
            "Override": Override,
        }
        return render(request, "bots/botuser_detail.html", context)


class VersionStartView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.prepare_version"

    def post(self, request, pk):
        bot_user = _bot_user(request, pk)
        try:
            draft = services.start_version(request=request, bot_user=bot_user)
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
            return redirect("bots:botuser_detail", pk=bot_user.pk)
        return redirect("bots:version_edit", pk=draft.pk)


class VersionEditView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.prepare_version"
    template_name = "bots/version_form.html"

    def _form(self, request, version, data=None):
        return VersionForm(
            data,
            instance=version,
            definitions=services.definitions_for(request.organization, version.robot_type),
            can_manage_real=request_has_perm(request, "bots.manage_real"),
        )

    def _guard(self, request, version):
        if not version.is_draft:
            messages.info(request, _("A validated version cannot be changed. Create a new version."))
            return redirect("bots:version_detail", pk=version.pk)
        if version.is_real and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied
        return None

    def get(self, request, pk):
        version = _version(request, pk)
        if (response := self._guard(request, version)) is not None:
            return response
        return render(request, self.template_name, {"form": self._form(request, version), "version": version})

    def post(self, request, pk):
        version = _version(request, pk)
        if (response := self._guard(request, version)) is not None:
            return response
        snapshot = ConfigurationVersion.objects.get(pk=version.pk)
        form = self._form(request, version, request.POST)
        if form.is_valid():
            data = {name: form.cleaned_data[name] for name in ("account_type", "reference_capital", "currency", "admin_note")}
            try:
                services.update_draft(request=request, version=snapshot, data=data, parameters=form.parameter_values())
            except ValidationError as exc:
                form.add_error(None, exc)
            except PermissionDenied as exc:
                _report(request, exc)
                return redirect("bots:botuser_detail", pk=version.bot_user_id)
            else:
                messages.success(request, _("The draft has been saved."))
                if request.POST.get("next") == "validate":
                    return redirect("bots:version_validate", pk=version.pk)
                return redirect("bots:version_detail", pk=version.pk)
        return render(request, self.template_name, {"form": form, "version": snapshot})


class VersionDeleteView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.prepare_version"

    def post(self, request, pk):
        version = _version(request, pk)
        bot_user_id = version.bot_user_id
        try:
            services.delete_draft(request=request, version=version)
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
            return redirect("bots:version_detail", pk=version.pk)
        messages.success(request, _("The draft has been deleted."))
        return redirect("bots:botuser_detail", pk=bot_user_id)


class VersionDetailView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.view_botuser"

    def get(self, request, pk):
        version = _version(request, pk)
        definitions = {d.key: d for d in ParameterDefinition.objects.filter(organization=request.organization, robot_type=version.robot_type)}
        parameters = [(p, definitions.get(p.key)) for p in version.parameters.all()]
        declarations = version.declarations.select_related("recorded_by", "corrects").order_by("-recorded_at")
        context = {
            "version": version,
            "bot_user": version.bot_user,
            "parameters": parameters,
            "declarations": declarations,
            "is_latest": services.latest_validated(version.bot_user) == version,
            "already_applied": services.effective_applied(version.bot_user).filter(version=version).exists(),
            "declare_form": DeclareAppliedForm(),
            "reason_form": ReasonForm(),
        }
        return render(request, "bots/version_detail.html", context)


class VersionValidateView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.validate_version"
    template_name = "bots/version_validate.html"

    def _context(self, version, real_form=None):
        return {
            "version": version,
            "bot_user": version.bot_user,
            "parameters": version.parameters.all(),
            "real_form": real_form or (RealDeclarationForm() if version.is_real else None),
            "wording": services.REAL_CONFIRMATION_WORDING,
        }

    def get(self, request, pk):
        version = _version(request, pk)
        if not version.is_draft:
            return redirect("bots:version_detail", pk=version.pk)
        if version.is_real and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied
        return render(request, self.template_name, self._context(version))

    def post(self, request, pk):
        version = _version(request, pk)
        if version.is_real and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied
        real_declaration = None
        real_form = None
        if version.is_real:
            real_form = RealDeclarationForm(request.POST)
            if not real_form.is_valid():
                return render(request, self.template_name, self._context(version, real_form))
            real_declaration = real_form.cleaned_data
        try:
            services.validate_version(request=request, version=version, real_declaration=real_declaration)
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
            return render(request, self.template_name, self._context(version, real_form))
        messages.success(request, _("Version %(number)s has been validated. It can no longer be changed.") % {"number": version.number})
        return redirect("bots:version_detail", pk=version.pk)


class DeclareAppliedView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.declare_applied"

    def post(self, request, pk):
        version = _version(request, pk)
        form = DeclareAppliedForm(request.POST)
        if form.is_valid():
            try:
                services.declare_applied(
                    request=request, version=version, applied_on=form.cleaned_data["applied_on"], note=form.cleaned_data["note"]
                )
            except (ValidationError, PermissionDenied) as exc:
                _report(request, exc)
            else:
                messages.success(request, _("The configuration has been declared applied. The platform does not check the VPS."))
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("bots:version_detail", pk=version.pk)


class CorrectDeclarationView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.correct_declaration"

    def post(self, request, pk):
        declaration = get_for_org(request, ApplicationDeclaration.objects.select_related("version"), pk=pk)
        form = ReasonForm(request.POST)
        if form.is_valid():
            try:
                services.correct_declaration(request=request, declaration=declaration, reason=form.cleaned_data["reason"])
            except (ValidationError, PermissionDenied) as exc:
                _report(request, exc)
            else:
                messages.success(request, _("The declaration has been corrected."))
        else:
            messages.error(request, _("A reason is required to correct a declaration."))
        return redirect("bots:version_detail", pk=declaration.version_id)


class OverrideView(OrgPermissionRequiredMixin, View):
    """Pause, désactivation et réactivation (permission vérifiée par le service)."""

    permission_required = "bots.view_botuser"

    def post(self, request, pk, action):
        bot_user = _bot_user(request, pk)
        mapping = {"pause": Override.PAUSED, "disable": Override.DISABLED, "reactivate": Override.NONE}
        if action not in mapping:
            raise PermissionDenied
        if not request_has_perm(request, "bots.pause" if action == "pause" else "bots.disable"):
            raise PermissionDenied
        form = ReasonForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("A reason is required."))
            return redirect("bots:botuser_detail", pk=bot_user.pk)
        try:
            services.set_override(request=request, bot_user=bot_user, override=mapping[action], reason=form.cleaned_data["reason"])
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
        else:
            messages.success(request, _("The status has been updated."))
        return redirect("bots:botuser_detail", pk=bot_user.pk)


class ParameterCatalogView(OrgPermissionRequiredMixin, View):
    permission_required = "bots.manage_parameters"
    template_name = "bots/parameters.html"

    def _robot(self, request):
        robot = request.GET.get("robot") or request.POST.get("robot") or RobotType.DIFFERS
        return robot if robot in RobotType.values else RobotType.DIFFERS

    def _queryset(self, request, robot):
        services.ensure_parameter_catalog(request.organization)
        return ParameterDefinition.objects.filter(organization=request.organization, robot_type=robot).order_by("key")

    def get(self, request):
        robot = self._robot(request)
        formset = ParameterDefinitionFormSet(queryset=self._queryset(request, robot))
        return render(request, self.template_name, {"formset": formset, "robot": robot, "robots": RobotType.choices})

    def post(self, request):
        robot = self._robot(request)
        formset = ParameterDefinitionFormSet(request.POST, queryset=self._queryset(request, robot))
        if formset.is_valid():
            with transaction.atomic():
                changed = []
                for form in formset.forms:
                    if form.has_changed():
                        definition = form.save(commit=False)
                        definition.updated_by = request.user
                        definition.save()
                        changed.append(definition.key)
                if changed:
                    audit.record(
                        "parameter_catalog_changed",
                        actor=request.user,
                        organization=request.organization,
                        robot_type=robot,
                        keys=changed,
                    )
            messages.success(request, _("The parameter list has been saved."))
            return redirect(f"{request.path}?robot={robot}")
        return render(request, self.template_name, {"formset": formset, "robot": robot, "robots": RobotType.choices})

