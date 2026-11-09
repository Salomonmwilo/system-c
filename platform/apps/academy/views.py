from django.views.generic import TemplateView

from apps.core.permissions import OrgPermissionRequiredMixin

from .models import Program


class AcademyHomeView(OrgPermissionRequiredMixin, TemplateView):
    permission_required = "academy.view"
    template_name = "academy/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["programs"] = Program.objects.filter(organization=self.request.organization).prefetch_related("courses")
        return context
