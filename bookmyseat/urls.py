from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # users app handles home, login, profile, test-email
    path("", include("users.urls")),

    # movies app
    path("movies/", include("movies.urls")),
]
