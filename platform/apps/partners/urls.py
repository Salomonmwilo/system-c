from django.urls import path

from . import views

app_name = "partners"

urlpatterns = [
    path("affiliates/", views.AffiliateListView.as_view(), name="affiliate_list"),
    path("affiliates/new/", views.AffiliateCreateView.as_view(), name="affiliate_create"),
    path("affiliates/<uuid:pk>/", views.AffiliateDetailView.as_view(), name="affiliate_detail"),
    path("affiliates/<uuid:pk>/edit/", views.AffiliateUpdateView.as_view(), name="affiliate_update"),
    path("affiliates/<uuid:pk>/archive/", views.AffiliateArchiveView.as_view(), name="affiliate_archive"),
    path("affiliates/<uuid:pk>/steps/<str:track>/", views.AffiliateTrackView.as_view(), name="affiliate_track"),
    path("affiliates/<uuid:pk>/interactions/", views.InteractionCreateView.as_view(), name="interaction_create"),
    path("affiliates/<uuid:pk>/followups/", views.FollowUpCreateView.as_view(), name="followup_create"),
    path("followups/", views.FollowUpListView.as_view(), name="followup_list"),
    path("followups/<uuid:pk>/close/", views.FollowUpCloseView.as_view(), name="followup_close"),
    path("referral-links/", views.ReferralLinkListView.as_view(), name="referral_links"),
    path("referral-links/<uuid:pk>/toggle/", views.ReferralLinkToggleView.as_view(), name="referral_link_toggle"),
]
