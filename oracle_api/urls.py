from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path("auth/token/", TokenObtainPairView.as_view(), name="api_token_obtain"),
    path("auth/google/", views.google_auth, name="api_google_auth"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),

    # Profile
    path("profile/", views.profile_view, name="api_profile"),

    # Wardrobe
    path("wardrobe/", views.wardrobe_list, name="api_wardrobe_list"),
    path("wardrobe/<int:item_id>/", views.wardrobe_detail, name="api_wardrobe_detail"),

    # Daily outfit
    path("daily-input/", views.daily_input, name="api_daily_input"),

    # Shopping Buddy
    path("shopping-buddy/", views.shopping_buddy_start, name="api_shopping_start"),
    path("shopping-buddy/<int:eval_id>/reply/", views.shopping_buddy_reply, name="api_shopping_reply"),
    path("shopping-buddy/<int:eval_id>/save/", views.shopping_save_toggle, name="api_shopping_save"),
    path("shopping-buddy/<int:eval_id>/share/", views.shopping_share, name="api_shopping_share"),
    path("shopping-buddy/history/", views.shopping_history, name="api_shopping_history"),
    path("shopping-buddy/wishlist/", views.shopping_wishlist, name="api_shopping_wishlist"),
    path("shopping-buddy/insights/", views.shopping_insights, name="api_shopping_insights"),
]
