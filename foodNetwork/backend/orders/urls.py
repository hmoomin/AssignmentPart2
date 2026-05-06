from django.urls import path
from .views import CartItemCreateView, CartItemListView, CheckoutView, CustomerDashboardView, EnvironmentalReportView, producer_dashboard_page, customer_dashboard_page, edit_product_page, delete_product_page, edit_education_page, delete_education_page, ProducerNotificationsView, CartItemUpdateView, CustomerNotificationsView, UpdateOrderItemView, ProducerOrdersView, MarkNotificationReadView, SafetyAlertView, ResolveProductView, DisableProductView, WeeklySettlementView, ConfirmPaymentView

urlpatterns = [
    # Order Items
    path("cart/items/", CartItemCreateView.as_view()),
    path("cart/", CartItemListView.as_view()),
    path("cart/items/<int:pk>/", CartItemUpdateView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    # Dashboards
    path("dashboard/producer/", ProducerOrdersView.as_view()),
    path("dashboard/customer/", CustomerDashboardView.as_view()),
    # Updates
    path("item/<int:pk>/", UpdateOrderItemView.as_view()),
    #Notifications
    path("notifications/", ProducerNotificationsView.as_view()),
    path("notifications/customer/", CustomerNotificationsView.as_view()),
    path("notifications/<int:pk>/read/", MarkNotificationReadView.as_view()),
    path("safety-alert/", SafetyAlertView.as_view()),
    path("product/<int:pk>/resolve/", ResolveProductView.as_view()),
    path("product/<int:pk>/disable/", DisableProductView.as_view()),
    path("confirm-payment/<int:order_id>/", ConfirmPaymentView.as_view()),
    # Reports
    path("report/<int:order_id>/", EnvironmentalReportView.as_view()),
    path("settlements/weekly/", WeeklySettlementView.as_view()),
    # Views (HTML)
    path("dashboard/producer/view/", producer_dashboard_page),
    path("dashboard/customer/view/", customer_dashboard_page),
    # Product/Education Management
    path("producer/products/edit/<int:id>/", edit_product_page),
    path("producer/products/delete/<int:id>/", delete_product_page),
    path("producer/education/edit/<int:id>/", edit_education_page),
    path("producer/education/delete/<int:id>/", delete_education_page),
]