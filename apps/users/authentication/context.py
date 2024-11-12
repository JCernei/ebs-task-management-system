from rest_framework.request import Request
from rest_framework.response import Response
from apps.users.authentication.strategies import (
    BaseAuthStrategy,
    GithubAuthenticationStrategy,
    EmailPasswordAuthenticationStrategy,
)


class AuthenticationContext:
    def __init__(self, strategy):
        self.strategies = {
            "github": GithubAuthenticationStrategy(),
            "email_password": EmailPasswordAuthenticationStrategy(),
        }

    def set_strategy(self, strategy: BaseAuthStrategy):
        self._strategy = strategy

    def authenticate(self, request: Request, strategy_name: str) -> Response:
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return Response({"detail": "Invalid authentication strategy"}, status=400)
