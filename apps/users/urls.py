from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import (
    RegisterUserView,
    UserListView,
    GithubAuthCallbackView,
    GitHubLoginRedirectView,
)

urlpatterns = [
    path("register", RegisterUserView.as_view(), name="token_register"),
    path("login", TokenObtainPairView.as_view(), name="login_user"),
    path("", UserListView.as_view(), name="user_list"),
    path("token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "login/github/redirect",
        GitHubLoginRedirectView.as_view(),
        name="github_login_redirect",
    ),
    path(
        "login/github/callback/",
        GithubAuthCallbackView.as_view(),
        name="github_auth_callback",
    ),
]
