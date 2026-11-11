from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("partners/", include("apps.partners.urls")),
    path("bots/", include("apps.bots.urls")),
    path("academy/", include("apps.academy.urls")),
]

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
