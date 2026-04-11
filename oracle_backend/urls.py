from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from oracle_frontend import views


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


urlpatterns = [
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
    path("shopping-buddy/", views.shopping_buddy_view, name="shopping_buddy"),
    path("shopping-buddy/<int:eval_id>/reply/", views.shopping_buddy_reply, name="shopping_buddy_reply"),
    path("shopping-buddy/<int:eval_id>/save/", views.shopping_save_for_later, name="shopping_save_for_later"),
    path("shopping-buddy/<int:eval_id>/share/", views.shopping_share_view, name="shopping_share"),
    path("shopping-buddy/shared/<str:token>/", views.shopping_shared_view, name="shopping_shared"),
    path("shopping-buddy/wishlist/", views.shopping_wishlist_view, name="shopping_wishlist"),
    path("shopping-buddy/insights/", views.shopping_insights_view, name="shopping_insights"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    from django.views.static import serve as static_serve
    from django.urls import re_path
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', static_serve, {'document_root': settings.BASE_DIR / 'static'}),
    ]
