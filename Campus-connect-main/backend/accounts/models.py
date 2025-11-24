from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    skills = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)  # lista de ids de proyectos a los que pertenece

    def __str__(self) -> str:
        return f"Profile({self.user.username})"
