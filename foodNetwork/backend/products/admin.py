from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "producer",
        "category",
        "price",
        "is_organic",
        "allergen_info",
        "best_before_date",
    )

    list_filter = (
        "category",
        "is_organic",
    )

    search_fields = (
        "name",
        "producer__username"
    )