from django.urls import path
from .views import RegisterView, login_view

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", login_view),
]