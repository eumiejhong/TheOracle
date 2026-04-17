from django.urls import path

from . import views

app_name = "listing_api"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("demo/", views.demo, name="demo"),
    path("docs/", views.docs, name="docs"),
    path("api/v1/health/", views.health, name="health"),
    path("api/v1/analyze/", views.analyze, name="analyze"),
]
