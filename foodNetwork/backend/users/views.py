from rest_framework import generics
from .models import User
from .serializers import UserSerializer
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from django.contrib import messages


class RegisterView(APIView):

    def post(self, request):
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            role = serializer.validated_data.get("role")

            user = serializer.save(
                is_producer=(role == "producer")
            )

            return Response({
                "message": "User created",
                "role": user.role
            }, status=201)

        return Response(serializer.errors, status=400)

@csrf_protect
def register_page(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")
        postcode = request.POST.get("postcode")

        # --- BASIC VALIDATION ---
        if User.objects.filter(username=username).exists():
            return render(request, "dashboards/register.html", {
                "error": "Username already exists"
            })

        if len(password) < 6:
            return render(request, "dashboards/register.html", {
                "error": "Password must be at least 6 characters"
            })

        if not postcode:
            return render(request, "dashboards/register.html", {
                "error": "Postcode is required"
            })

        # --- POSTCODE VALIDATION + GEOCODING ---
        try:
            response = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
            data = response.json()

            if data["status"] != 200:
                raise Exception("Invalid postcode")

            latitude = data["result"]["latitude"]
            longitude = data["result"]["longitude"]

        except Exception:
            return render(request, "dashboards/register.html", {
                "error": "Invalid postcode entered"
            })

        # --- CREATE USER ---
        user = User.objects.create_user(
            username=username,
            password=password,
            role=role,
            postcode=postcode,
            latitude=latitude,
            longitude=longitude,
            is_producer=(role == "producer")
        )

        return redirect("/login/")

    return render(request, "dashboards/register.html")

def home_page(request):
    if request.user.is_authenticated:
        if request.user.is_producer:
            return redirect("/api/orders/dashboard/producer/view/")
        return redirect("/api/orders/dashboard/customer/view/")
    
    return render(request, "dashboards/home.html")

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