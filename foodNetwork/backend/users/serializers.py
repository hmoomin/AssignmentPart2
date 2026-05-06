from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password", "role"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "role",
            "postcode",
            "address",
            "phone"
        ]

    def validate_role(self, value):
        if value not in ["customer", "producer"]:
            raise serializers.ValidationError("Invalid role")
        return value

    def create(self, validated_data):
        role = validated_data.get("role")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
            role=role,
            is_producer=(role == "producer"),
            postcode=validated_data.get("postcode", ""),
            address=validated_data.get("address", ""),
            phone=validated_data.get("phone", "")
        )
        return user