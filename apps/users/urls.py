from django.urls import path

from apps.users.views import (
    RegisterUserView,
    UserListView,
    GithubAuthCallbackView,
    GitHubLoginRedirectView,
    AuthenticationView,
)

urlpatterns = [
    path("register", RegisterUserView.as_view(), name="token_register"),
    path("login", AuthenticationView.as_view(), name="login_user"),
    path("", UserListView.as_view(), name="user_list"),
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
