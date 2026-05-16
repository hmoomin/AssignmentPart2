from rest_framework import serializers
from .models import Product, EducationalContent


class ProductSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.username", read_only=True)
    is_available = serializers.SerializerMethodField()
    is_in_season = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_discounted = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "unit",
            "discounted_price",
            "category",
            "is_organic",
            "allergen_info",
            "origin_farm",
            "harvest_date",
            "available_from",
            "available_to",
            "best_before_date",
            "delivery_method",
            "delivery_notes",
            "stock_quantity",
            "producer",
            "producer_name",
            "is_available",
            "is_in_season",
            "discounted_price",
            "discount_percentage",
            "is_discounted",
            "status",
        ]
        read_only_fields = ["producer"]

    def get_is_available(self, obj):
        return obj.is_available()

    def get_is_in_season(self, obj):
        return obj.is_in_season()

    def get_discounted_price(self, obj):
        return obj.discounted_price
    
    def get_discount_percentage(self, obj):
        discount = obj.get_active_discount()
        return discount if discount else 0

    def get_is_discounted(self, obj):
        return obj.get_active_discount() is not None

class EducationalContentSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.username", read_only=True)
    
    class Meta:
        model = EducationalContent
        fields = [
            "id",
            "content_type",
            "title",
            "content",
            "producer",
            "producer_name",
            "created_at",
        ]
        read_only_fields = ["producer"]