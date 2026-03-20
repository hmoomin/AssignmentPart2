from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

User = settings.AUTH_USER_MODEL

class Product(models.Model):
    producer = models.ForeignKey(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

    CATEGORY_CHOICES = [
        ("vegetables", "Vegetables"),
        ("dairy", "Dairy"),
        ("bakery", "Bakery"),
        ("preserves", "Preserves"),
        ("seasonal", "Seasonal"),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    is_organic = models.BooleanField(default=False)
    allergen_info = models.TextField(blank=True)
    best_before_date = models.DateField(null=True, blank=True)

    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)

    stock_quantity = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_available(self):
        today = timezone.now().date()

        if self.stock_quantity <= 0:
            return False

        if self.available_from and today < self.available_from:
            return False

        if self.available_to and today > self.available_to:
            return False

        if self.best_before_date and today > self.best_before_date:
            return False

        return True

    def get_active_discount(self):
        now = timezone.now()
        return self.discount_set.filter(
            start_date__lte=now,
            end_date__gte=now
        ).first()

    def discounted_price(self):
        discount = self.get_active_discount()
        if discount:
            return self.price * (1 - discount.discount_percentage / 100)
        return self.price

    def auto_apply_expiry_discount(self):
        if self.best_before_date:
            days_left = (self.best_before_date - timezone.now().date()).days
            if days_left <= 2:
                Discount.objects.create(
                    product=self,
                    discount_percentage=30,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=2)
                )


class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percentage = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()


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