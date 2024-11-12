from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.authentication.context import AuthenticationContext
from apps.users.authentication.strategies import GithubAuthenticationStrategy
from apps.users.models import User
from apps.users.serializers import (
    UserSerializer,
    UserListSerializer,
    GitHubLoginRedirectSerializer,
)


class RegisterUserView(GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request: Request) -> Response:
        #  Validate data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Get password from validated data
        password = validated_data.pop("password")

        # Create user
        user = User.objects.create(
            **validated_data,
            is_superuser=True,
            is_staff=True,
        )

        # Set password
        user.set_password(password)
        user.save()

        # Generate JWT token
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        )


class UserListView(ListAPIView):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]


class GitHubLoginRedirectView(GenericAPIView):
    serializer_class = GitHubLoginRedirectSerializer
    authentication_classes = []
    permission_classes = []

    @extend_schema(description="Redirect to github authentication")
    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(redirect_to=f"{settings.GITHUB_AUTH_REDIRECT}")


class GithubAuthCallbackView(SocialLoginView):
    authentication_classes = []
    permission_classes = []
    http_method_names = ["get"]

    @extend_schema(description="Get Github auth code")
    def get(self, request, *args, **kwargs):
        strategy = GithubAuthenticationStrategy()
        context = AuthenticationContext(strategy)
        return context.authenticate(request)


class AuthenticationView(GenericAPIView):
    def post(self, request: Request) -> Response:
        # Check if the request is for GitHub authentication
        if request.data.get("strategy") == "github":
            return self.handle_github_auth(request)

        # Otherwise, use the AuthenticationContext to handle the authentication
        auth_context = AuthenticationContext
        strategy_name = request.data.get("strategy", "email_password")
        response, success = auth_context.authenticate(request, strategy_name)

        if success:
            return response
        else:
            return response

    def handle_github_auth(self, request: Request) -> Response:
        code = request.query_params.get("code")
        if not code:
            return Response({"detail": "No authorization code provided"}, status=400)

        request.data["code"] = code
        adapter_class = GitHubOAuth2Adapter
        client_class = OAuth2Client
        callback_url = settings.REDIRECT_URI

        # Use the dj-rest-auth SocialLoginView to handle the GitHub authentication
        view = SocialLoginView.as_view(
            adapter_class=adapter_class,
            client_class=client_class,
            callback_url=callback_url,
        )
        return view(request)
