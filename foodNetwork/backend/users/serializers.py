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
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "confirm_password",
            "role",
            "business_name",
            "contact_name",
            "postcode",
            "address",
            "phone"
        ]

    # Validate role
    def validate_role(self, value):
        if value not in ["customer", "producer"]:
            raise serializers.ValidationError("Invalid role")
        return value

    # Validate email uniqueness
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    # Validate password match
    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        if len(data["password"]) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters")
        return data

    def create(self, validated_data):
        from products.utils import postcode_to_coords

        validated_data.pop("confirm_password")

        postcode = validated_data.get("postcode")

        # Convert postcode to lat/lon
        lat, lon = postcode_to_coords(postcode)
        if lat is None or lon is None:
            raise serializers.ValidationError("Invalid postcode")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            role=validated_data["role"],
            is_producer=(validated_data["role"] == "producer"),
            business_name=validated_data.get("business_name", ""),
            contact_name=validated_data.get("contact_name", ""),
            postcode=postcode,
            address=validated_data.get("address", ""),
            phone=validated_data.get("phone", ""),
            latitude=lat,
            longitude=lon
        )

        return user