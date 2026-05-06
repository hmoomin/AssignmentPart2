from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from orders.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class Product(models.Model):
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    CATEGORY_CHOICES = [
        ("vegetables", "Vegetables"),
        ("dairy", "Dairy"),
        ("bakery", "Bakery"),
        ("preserves", "Preserves"),
        ("seasonal", "Seasonal"),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    # Product quality + compliance
    is_organic = models.BooleanField(default=False)
    allergen_info = models.TextField(blank=True)
    # Supply chain info
    origin_farm = models.CharField(max_length=255, blank=True)
    harvest_date = models.DateField(null=True, blank=True)
    # Availability window
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)
    # Expiry
    best_before_date = models.DateField(null=True, blank=True)
    # Inventory
    stock_quantity = models.IntegerField(default=0)
    is_recalled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    discount_end_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ("active", "Active"),
        ("recalled", "Recalled"),
        ("disabled", "Disabled"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )
    # Delivery
    DELIVERY_CHOICES = [
        ("pickup", "Pickup"),
        ("delivery", "Delivery"),
    ]

    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default="pickup"
    )
    delivery_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["producer"]),
            models.Index(fields=["available_from", "available_to"]),
        ]

    def is_available(self):
        today = timezone.now().date()
        if self.is_recalled:
            return False

        if not self.is_active:
            return False

        if self.stock_quantity <= 0:
            return False

        if self.available_from and today < self.available_from:
            return False

        if self.available_to and today > self.available_to:
            return False

        if self.best_before_date and today > self.best_before_date:
            return False

        return True

    def is_in_season(self):
        today = timezone.now().date()
        if self.available_from and self.available_to:
            return self.available_from <= today <= self.available_to
        return False

    def get_active_discount(self):
        if self.discount_percentage > 0 and self.discount_end_date:
            if self.discount_end_date >= timezone.now():
                return self.discount_percentage
        return None

    @property
    def discounted_price(self):
        if self.discount_percentage > 0:
            return self.price * (
                Decimal("1") - Decimal(self.discount_percentage) / Decimal("100")
            )
        return self.price

    def auto_apply_expiry_discount(self):
        if self.best_before_date:
            days_left = (self.best_before_date - timezone.now().date()).days
            active_discount = self.discount_set.filter(
                end_date__gte=timezone.now()
            ).exists()
            if days_left <= 2 and not active_discount:
                discount = Discount.objects.create(
                    product=self,
                    discount_percentage=30,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=2)
                )
                users = User.objects.filter(is_producer=False)
                for user in users:
                    already_notified = Notification.objects.filter(
                        user=user,
                        notification_type="discount",
                        message__icontains=self.name
                    ).exists()
                    if not already_notified:
                        Notification.objects.create(
                            user=user,
                            message=f"🔻 {self.name} is now {discount.discount_percentage}% off!",
                            notification_type="discount"
                        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            self.auto_apply_expiry_discount()
        except Exception as e:
            print("Discount error:", e)

    def clean(self):
        if self.available_from and self.available_to:
            if self.available_from > self.available_to:
                raise ValidationError("Available from cannot be after available to.")

    def __str__(self):
        return self.name


class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percentage = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Sync to product
        self.product.discount_percentage = self.discount_percentage
        self.product.discount_end_date = self.end_date
        self.product.save(update_fields=["discount_percentage", "discount_end_date"])

class EducationalContent(models.Model):
    CONTENT_TYPES = [
        ("recipe", "Recipe"),
        ("storage", "Storage"),
        ("story", "Farm Story"),
    ]
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type"]),
            models.Index(fields=["producer"]),
        ]

    def __str__(self):
        return self.title