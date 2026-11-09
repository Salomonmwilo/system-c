from django.urls import path

from . import views

app_name = "bots"

urlpatterns = [
    path("", views.BotUserListView.as_view(), name="botuser_list"),
    path("new/", views.BotUserCreateView.as_view(), name="botuser_create"),
    path("parameters/", views.ParameterCatalogView.as_view(), name="parameters"),
    path("<uuid:pk>/", views.BotUserDetailView.as_view(), name="botuser_detail"),
    path("<uuid:pk>/edit/", views.BotUserUpdateView.as_view(), name="botuser_update"),
    path("<uuid:pk>/versions/new/", views.VersionStartView.as_view(), name="version_start"),
    path("<uuid:pk>/status/<str:action>/", views.OverrideView.as_view(), name="botuser_override"),
    path("versions/<uuid:pk>/", views.VersionDetailView.as_view(), name="version_detail"),
    path("versions/<uuid:pk>/edit/", views.VersionEditView.as_view(), name="version_edit"),
    path("versions/<uuid:pk>/delete/", views.VersionDeleteView.as_view(), name="version_delete"),
    path("versions/<uuid:pk>/validate/", views.VersionValidateView.as_view(), name="version_validate"),
    path("versions/<uuid:pk>/declare-applied/", views.DeclareAppliedView.as_view(), name="version_declare_applied"),
    path("declarations/<int:pk>/correct/", views.CorrectDeclarationView.as_view(), name="declaration_correct"),
]
