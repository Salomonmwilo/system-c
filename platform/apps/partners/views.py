from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import View

from apps.core import audit
from apps.core.models import OrganizationSettings
from apps.core.permissions import OrgPermissionRequiredMixin, get_for_org, request_has_perm
from apps.core.registry import affiliate_panels

from . import services
from .forms import AffiliateFilterForm, AffiliateForm, FollowUpForm, InteractionForm, ReferralLinkForm, TrackForm
from .models import TRACK_FIELDS, Affiliate, ReferralLink, Track


def _affiliate(request, pk) -> Affiliate:
    """Affilié de l'organisation courante et visible par l'utilisateur, sinon 404."""
    return get_object_or_404(services.visible_affiliates(request), pk=pk)


def _form_errors_to_messages(request, form) -> None:
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


class AffiliateListView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.view_affiliate"

    def get(self, request):
        form = AffiliateFilterForm(request.GET or None)
        queryset = services.visible_affiliates(request).select_related("assigned_to")
        settings_obj = OrganizationSettings.for_organization(request.organization)
        show_archived = False
        if form.is_valid():
            data = form.cleaned_data
            show_archived = data["archived"]
            if data["q"]:
                term = data["q"].strip()
                condition = Q(display_name__icontains=term)
                if request_has_perm(request, "partners.view_pii"):
                    condition |= Q(email__icontains=term) | Q(phone__icontains=term)
                queryset = queryset.filter(condition)
            if data["status"]:
                queryset = queryset.filter(status=data["status"])
            if data["registration"]:
                queryset = queryset.filter(registration_status=data["registration"])
            if data["verification"]:
                queryset = queryset.filter(verification_status=data["verification"])
            if data["alert"] in services.ALERTS:
                queryset = services.ALERTS[data["alert"]](queryset, settings_obj)
        queryset = queryset if show_archived else queryset.filter(archived_at__isnull=True)
        page = Paginator(queryset.order_by("display_name"), 25).get_page(request.GET.get("page"))
        return render(request, "partners/affiliate_list.html", {"filter_form": form, "page": page})


class AffiliateCreateView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.add_affiliate"
    template_name = "partners/affiliate_form.html"

    def get(self, request):
        form = AffiliateForm(organization=request.organization)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = AffiliateForm(request.POST, organization=request.organization)
        if form.is_valid():
            try:
                affiliate = services.create_affiliate(organization=request.organization, actor=request.user, data=form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, _("The affiliate has been created."))
                return redirect("partners:affiliate_detail", pk=affiliate.pk)
        return render(request, self.template_name, {"form": form})


class AffiliateUpdateView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.change_affiliate"
    template_name = "partners/affiliate_form.html"

    def get(self, request, pk):
        affiliate = _affiliate(request, pk)
        form = AffiliateForm(instance=affiliate, organization=request.organization)
        return render(request, self.template_name, {"form": form, "affiliate": affiliate})

    def post(self, request, pk):
        affiliate = _affiliate(request, pk)
        snapshot = Affiliate.objects.get(pk=affiliate.pk)
        form = AffiliateForm(request.POST, instance=affiliate, organization=request.organization)
        if form.is_valid():
            try:
                services.update_affiliate(affiliate=snapshot, actor=request.user, data=form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, _("The affiliate has been updated."))
                return redirect("partners:affiliate_detail", pk=affiliate.pk)
        return render(request, self.template_name, {"form": form, "affiliate": snapshot})


class AffiliateDetailView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.view_affiliate"

    def get(self, request, pk):
        affiliate = _affiliate(request, pk)
        tracks = []
        for key in (Track.REGISTRATION, Track.VERIFICATION, Track.DEMO):
            status_field, date_field, _choices = TRACK_FIELDS[key]
            raw = getattr(affiliate, status_field)
            tracks.append(
                {
                    "key": key,
                    "label": Track(key).label,
                    "raw": raw,
                    "value": getattr(affiliate, f"get_{status_field}_display")(),
                    "date": getattr(affiliate, date_field),
                    "form": TrackForm(track=key, current=raw),
                }
            )
        context = {
            "affiliate": affiliate,
            "tracks": tracks,
            "track_events": affiliate.track_events.select_related("recorded_by")[:50],
            "interactions": affiliate.interactions.select_related("author")[:50],
            "followups": affiliate.followups.select_related("assigned_to").order_by("-status", "due_on")[:50],
            "interaction_form": InteractionForm(),
            "followup_form": FollowUpForm(organization=request.organization),
            "panels": affiliate_panels(request, affiliate.pk),
        }
        return render(request, "partners/affiliate_detail.html", context)


class AffiliateTrackView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.update_tracks"

    def post(self, request, pk, track):
        affiliate = _affiliate(request, pk)
        if track not in Track.values:
            raise Http404
        form = TrackForm(request.POST, track=track)
        if form.is_valid():
            data = form.cleaned_data
            try:
                services.record_track(
                    affiliate=affiliate,
                    actor=request.user,
                    track=track,
                    value=data["value"],
                    declared_on=data["declared_on"],
                    source=data["source"],
                    note=data["note"],
                )
            except ValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
            else:
                messages.success(request, _("The step has been recorded."))
        else:
            _form_errors_to_messages(request, form)
        return redirect("partners:affiliate_detail", pk=affiliate.pk)


class InteractionCreateView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.add_interaction"

    def post(self, request, pk):
        affiliate = _affiliate(request, pk)
        form = InteractionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                services.add_interaction(
                    affiliate=affiliate, actor=request.user, kind=data["kind"], occurred_at=data["occurred_at"], summary=data["summary"]
                )
            except ValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
            else:
                messages.success(request, _("The interaction has been added."))
        else:
            _form_errors_to_messages(request, form)
        return redirect("partners:affiliate_detail", pk=affiliate.pk)


class FollowUpCreateView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.manage_followups"

    def post(self, request, pk):
        affiliate = _affiliate(request, pk)
        form = FollowUpForm(request.POST, organization=request.organization)
        if form.is_valid():
            data = form.cleaned_data
            services.create_followup(
                affiliate=affiliate,
                actor=request.user,
                title=data["title"],
                due_on=data["due_on"],
                assigned_to=data["assigned_to"],
                note=data["note"],
            )
            messages.success(request, _("The follow-up has been scheduled."))
        else:
            _form_errors_to_messages(request, form)
        return redirect("partners:affiliate_detail", pk=affiliate.pk)


class FollowUpCloseView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.manage_followups"

    def post(self, request, pk):
        followup = get_object_or_404(services.open_followups(request), pk=pk)
        status = request.POST.get("status", "")
        try:
            services.close_followup(followup=followup, actor=request.user, status=status)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
        else:
            messages.success(request, _("The follow-up has been updated."))
        target = request.POST.get("return_to")
        if target == "list":
            return redirect("partners:followup_list")
        return redirect("partners:affiliate_detail", pk=followup.affiliate_id)


class AffiliateArchiveView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.archive_affiliate"

    def post(self, request, pk):
        affiliate = _affiliate(request, pk)
        archive = request.POST.get("action") != "restore"
        services.set_archived(affiliate=affiliate, actor=request.user, archived=archive)
        messages.success(request, _("The affiliate has been archived.") if archive else _("The affiliate has been restored."))
        return redirect("partners:affiliate_detail", pk=affiliate.pk)


class FollowUpListView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.view_followups"

    def get(self, request):
        queryset = services.open_followups(request).select_related("affiliate", "assigned_to")
        scope = request.GET.get("scope", "all")
        if scope == "mine":
            queryset = queryset.filter(assigned_to=request.user)
        page = Paginator(queryset.order_by("due_on", "created_at"), 50).get_page(request.GET.get("page"))
        return render(request, "partners/followup_list.html", {"page": page, "scope": scope})


class ReferralLinkListView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.manage_referral_links"

    def get(self, request):
        links = ReferralLink.objects.filter(organization=request.organization)
        return render(request, "partners/referral_links.html", {"links": links, "form": ReferralLinkForm()})

    def post(self, request):
        form = ReferralLinkForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.organization = request.organization
            link.created_by = request.user
            link.save()
            audit.record("referral_link_created", actor=request.user, organization=request.organization, target=link)
            messages.success(request, _("The referral link has been saved."))
            return redirect("partners:referral_links")
        links = ReferralLink.objects.filter(organization=request.organization)
        return render(request, "partners/referral_links.html", {"links": links, "form": form})


class ReferralLinkToggleView(OrgPermissionRequiredMixin, View):
    permission_required = "partners.manage_referral_links"

    def post(self, request, pk):
        link = get_for_org(request, ReferralLink, pk=pk)
        link.is_active = not link.is_active
        link.save(update_fields=["is_active"])
        audit.record("referral_link_toggled", actor=request.user, organization=request.organization, target=link, active=link.is_active)
        return redirect("partners:referral_links")

