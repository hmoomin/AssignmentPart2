"""marketplace URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from users.views import logout_user, change_password
from orders.views import add_product_page, add_education_page, edit_product_page, delete_product_page, edit_education_page, delete_education_page, customer_dashboard_page
from products.views import review_page
from users.views import RegisterView, register_page, home_page

urlpatterns = [
    path('admin/', admin.site.urls),
    # API
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api-auth/', include('rest_framework.urls')),
    # Users / pages
    path("", include("users.urls")),
    path("home/", home_page),
    path("register/", register_page),
    path("api/register/", RegisterView.as_view()),
    path("logout/", logout_user),
    path("change-password/", change_password),
    # dashboards
    path("producer/add-product/", add_product_page),
    path("producer/add-education/", add_education_page),
    path("producer/edit-product/<int:pk>/", edit_product_page),
    path("producer/delete-product/<int:pk>/", delete_product_page),
    path("producer/edit-education/<int:pk>/", edit_education_page),
    path("producer/delete-education/<int:pk>/", delete_education_page),

    path("review/", review_page),
    path("dashboard/customer/view/", customer_dashboard_page),
]