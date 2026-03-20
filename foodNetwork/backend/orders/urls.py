from django.urls import path
from .views import CartItemCreateView, CartItemListView, CheckoutView, CustomerDashboardView, ProducerDashboardView, SustainabilityReportView, producer_dashboard_page, customer_dashboard_page, edit_product_page, delete_product_page, edit_education_page, delete_education_page

urlpatterns = [
    path("cart/add/", CartItemCreateView.as_view()),
    path("cart/", CartItemListView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("dashboard/customer/", CustomerDashboardView.as_view()),
    path("dashboard/producer/", ProducerDashboardView.as_view()),
    path("reports/sustainability/", SustainabilityReportView.as_view()),
    path("dashboard/producer/view/", producer_dashboard_page),
    path("dashboard/customer/view/", customer_dashboard_page),
    path("producer/products/edit/<int:id>/", edit_product_page),
    path("producer/products/delete/<int:id>/", delete_product_page),
    path("producer/education/edit/<int:id>/", edit_education_page),
    path("producer/education/delete/<int:id>/", delete_education_page),
]