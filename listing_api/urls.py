from django.urls import path

from . import eval_views, views

app_name = "listing_api"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("demo/", views.demo, name="demo"),
    path("docs/", views.docs, name="docs"),
    path("api/v1/health/", views.health, name="health"),
    path("api/v1/analyze/", views.analyze, name="analyze"),

    # Eval / ground-truth labeling (dev + staff only; gated inside the views)
    path("eval/", eval_views.label_index, name="label_index"),
    path("eval/save/", eval_views.save_label, name="save_label"),
    path("eval/<str:item_id>/delete/", eval_views.delete_label, name="delete_label"),
    path("eval/<str:item_id>/photo/<str:filename>", eval_views.item_photo, name="item_photo"),
]
