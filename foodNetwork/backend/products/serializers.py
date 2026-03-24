from rest_framework import serializers
from .models import Product, EducationalContent

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["producer"]

class EducationalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalContent
        fields = "__all__"
        read_only_fields = ["producer"]