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
    authentication_classes = ()
    permission_classes = (AllowAny,)
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.REDIRECT_URI
    http_method_names = ["get"]

    @extend_schema(description="Get Github auth code")
    def get(self, request, *args, **kwargs):
        code = request.query_params.get("code")
        if not code:
            return Response({"detail": "No authorization code provided"}, status=400)

        request.data["code"] = code
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            refresh = RefreshToken.for_user(request.user)
            return Response(
                {"refresh": str(refresh), "access": str(refresh.access_token)}
            )

        return Response({"detail": "Failed to authenticate with GitHub"}, status=400)
