from rest_framework import generics
from .models import User
from .serializers import RegisterSerializer
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
        serializer = RegisterSerializer(data=request.data)
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
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role")
        business_name = request.POST.get("business_name")
        contact_name = request.POST.get("contact_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        postcode = request.POST.get("postcode")

        # --- VALIDATION ---
        if User.objects.filter(username=username).exists():
            return render(request, "dashboards/register.html", {"error": "Username already exists"})
        if User.objects.filter(email=email).exists():
            return render(request, "dashboards/register.html", {"error": "Email already exists"})
        if password != confirm_password:
            return render(request, "dashboards/register.html", {"error": "Passwords do not match"})
        if len(password) < 6:
            return render(request, "dashboards/register.html", {"error": "Password must be at least 6 characters"})
        if not postcode:
            return render(request, "dashboards/register.html", {"error": "Postcode is required"})
        # --- POSTCODE VALIDATION ---
        try:
            response = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
            data = response.json()
            if data["status"] != 200:
                raise Exception()
            latitude = data["result"]["latitude"]
            longitude = data["result"]["longitude"]
        except Exception:
            return render(request, "dashboards/register.html", {"error": "Invalid postcode"})
        # --- CREATE USER ---
        user = User.objects.create_user(
            username=username,
            password=password,
            role=role,
            business_name=business_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
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