from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CurriculumConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.curriculum"
    verbose_name = _("Curriculum")
