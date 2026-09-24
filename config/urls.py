from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import set_language

urlpatterns = [
    path("admin/", admin.site.urls),
    # Native Django language switcher (POST language=<code>&next=<url>). It rewrites
    # the language prefix of `next`, so users stay on the same page.
    path("i18n/setlang/", set_language, name="set_language"),
]

# Public pages live under /fr/... and /en/... (prefix is the source of truth).
urlpatterns += i18n_patterns(
    path("", include("apps.curriculum.urls")),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
