from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("apps.tasks.urls")),
    path("common/", include("apps.common.urls")),
    path("users/", include("apps.users.urls")),
]
