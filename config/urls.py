from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("admin/", admin.site.urls),
    path("", include("apps.tasks.urls")),
    path("common/", include("apps.common.urls")),
    path("users/", include("apps.users.urls")),
]
