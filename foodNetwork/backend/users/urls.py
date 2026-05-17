from django.urls import path
from .views import login_view, UserProfileView

urlpatterns = [
    path("login/", login_view),
    path("users/profile/", UserProfileView.as_view()),
]