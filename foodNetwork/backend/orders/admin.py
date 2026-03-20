from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):

    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer",
        "status",
        "created_at",
        "commission"
    )

    list_filter = (
        "status",
        "created_at"
    )

    search_fields = (
        "customer__username",
    )

    inlines = [OrderItemInline]

    def commission(self, obj):
        return obj.commission()

    commission.short_description = "Platform Commission"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "product",
        "producer",
        "quantity",
        "price"
    )

    list_filter = (
        "producer",
    )

    search_fields = (
        "product__name",
    )

# NOT giving the admin access to the carts and cart items.