from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate


class BaseAuthStrategy:
    def authenticate(self, request: Request) -> Response:
        raise NotImplementedError("Subclasses must implement 'authenticate' method")


class GithubAuthenticationStrategy(SocialLoginView, BaseAuthStrategy):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.REDIRECT_URI

    def authenticate(self, request) -> Response:
        code = request.query_params.get("code")
        if not code:
            return Response({"detail": "No authorization code provided"}, status=400)

        request.data["code"] = code
        response = super().post(request)

        if response.status_code == 200:
            refresh = RefreshToken.for_user(request.user)
            return Response(
                {"refresh": str(refresh), "access": str(refresh.access_token)}
            )

        return Response({"detail": "Failed to authenticate with GitHub"}, status=400)


class EmailPasswordAuthenticationStrategy(BaseAuthStrategy):
    def authenticate(self, request: Request) -> Response:
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            response = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
            return Response(response)
        else:
            return Response({"detail": "Invalid email or password"}, status=400)
