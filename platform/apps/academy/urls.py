from django.urls import path

from . import views

app_name = "academy"

urlpatterns = [path("", views.AcademyHomeView.as_view(), name="home")]
