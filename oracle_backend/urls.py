from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from oracle_frontend import views
import os


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def debug_static(request):
    static_root = str(settings.STATIC_ROOT)
    static_dirs = [str(d) for d in settings.STATICFILES_DIRS]
    root_exists = os.path.exists(static_root)
    css_path = os.path.join(static_root, 'css', 'oracle.css')
    css_exists = os.path.exists(css_path)
    files_in_root = []
    if root_exists:
        for dirpath, dirnames, filenames in os.walk(static_root):
            for f in filenames:
                files_in_root.append(os.path.relpath(os.path.join(dirpath, f), static_root))
    source_exists = os.path.exists(os.path.join(str(settings.BASE_DIR), 'static', 'css', 'oracle.css'))
    return JsonResponse({
        "STATIC_ROOT": static_root,
        "STATIC_ROOT_exists": root_exists,
        "STATICFILES_DIRS": static_dirs,
        "css_in_root": css_exists,
        "source_css_exists": source_exists,
        "files_in_staticfiles": files_in_root[:50],
        "STATIC_URL": settings.STATIC_URL,
        "DEBUG": settings.DEBUG,
        "STORAGES": getattr(settings, 'STORAGES', 'not set'),
    })


urlpatterns = [
    path("debug-static/", debug_static),
    path("", landing_page, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.base_style_profile_view, name="base_profile"),
    path("profile/saved/", views.profile_saved_view, name="profile_saved"),
    path("daily-input/", views.daily_style_input_view, name="daily_input"),
    path("outfit/<int:suggestion_id>/", views.suggestion_detail_view, name="suggestion_detail"),
    path("wardrobe/mark-worn/<int:item_id>/", views.mark_item_as_worn, name="mark_item_as_worn"),
    path("feedback/<int:suggestion_id>/", views.submit_feedback, name="submit_feedback"),
    path("toggle-favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("add-from-daily/", views.add_from_daily_view, name="add_from_daily_view"),
    path("wardrobe/delete/", views.delete_wardrobe_item, name="delete_wardrobe_item"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
