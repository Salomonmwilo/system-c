from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("language/", views.switch_language, name="switch_language"),
    path("organization/", views.switch_organization, name="switch_organization"),
    path("no-organization/", views.no_organization, name="no_organization"),
    path("account/password/", views.ProfilePasswordView.as_view(), name="password_change"),
    path("settings/members/", views.MemberListView.as_view(), name="members"),
    path("settings/members/new/", views.MemberCreateView.as_view(), name="member_create"),
    path("settings/members/<uuid:user_id>/roles/", views.MemberRolesView.as_view(), name="member_roles"),
    path("settings/alerts/", views.ThresholdsView.as_view(), name="thresholds"),
    path("settings/audit/", views.AuditLogView.as_view(), name="audit"),
]
