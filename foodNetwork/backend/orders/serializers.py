from rest_framework import serializers
from .models import CartItem, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    producer_name = serializers.CharField(source="product.producer.username", read_only=True)
    delivery_method = serializers.CharField(source="product.delivery_method", read_only=True)
    price = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "producer_name",
            "delivery_method",
            "quantity",
            "price",
            "subtotal",
        ]

    def get_price(self, obj):
        return obj.product.discounted_price

    def get_subtotal(self, obj):
        return obj.product.discounted_price * obj.quantity
    
class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    order_date = serializers.DateTimeField(source="order.created_at", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    payment_status = serializers.CharField(source="order.payment_status", read_only=True)
    food_miles = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "order_date",
            "order_status",
            "product_name",
            "producer",
            "producer_name",
            "quantity",
            "price",
            "subtotal",
            "status",
            "payment_status",
            "delivery_time",
            "delivery_method",
            "delivery_notes",
            "food_miles",
        ]

    def get_subtotal(self, obj):
        return obj.price * obj.quantity

    def get_food_miles(self, obj):
        return obj.food_miles