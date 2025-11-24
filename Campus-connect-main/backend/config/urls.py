from django.contrib import admin
from django.urls import path
from api import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("", views.frontend_index, name="home"),
    path("admin/", admin.site.urls),
    path("api/health/", views.health),
    path("api/me/", views.me),
    path("api/recommendations/", views.dashboard_recommendations, name="recommendations"),
    path("api/skills/", views.skills, name="skills"),
    path("api/projects/join/", views.join_project, name="join_project"),
    path("api/chat/", views.chat_messages, name="chat_messages"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
