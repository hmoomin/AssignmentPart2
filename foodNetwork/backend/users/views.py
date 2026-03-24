from rest_framework import generics
from .models import User
from .serializers import UserSerializer
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    serializer_class = UserSerializer

def login_home(request):
    return render(request, "dashboards/login.html")

@csrf_protect
def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            login(request, user)

            if user.is_superuser:
                return redirect("/admin/")

            if user.is_producer:
                return redirect("/api/orders/dashboard/producer/view/")

            return redirect("/api/orders/dashboard/customer/view/")

        return render(
            request,
            "dashboards/login.html",
            {"error": "Invalid username or password"}
        )

    return render(request, "dashboards/login.html")

def logout_user(request):

    logout(request)

    return redirect("/login/")

@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():

            user = form.save()
            update_session_auth_hash(request, user)

            return redirect("/")

    else:

        form = PasswordChangeForm(request.user)

    return render(request, "dashboards/changePassword.html", {"form": form})