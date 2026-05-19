from django.db import models
from django.conf import settings
from django.utils import timezone


User = settings.AUTH_USER_MODEL

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.user}'s cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.discounted_price * self.quantity
    
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    # Payment
    payment_status = models.CharField(max_length=20, default="processing")

    is_bulk_order = models.BooleanField(default=False)
    special_instructions = models.TextField(blank=True)

    is_recurring_instance = models.BooleanField(default=False)
    recurring_parent = models.ForeignKey(
        "RecurringOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_COMPLETED, "Completed"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())

    def __str__(self):
        return f"Order {self.id} - {self.customer}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200, default="Unknown Product")
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    producer_name = models.CharField(max_length=200, default="Unknown Producer")
    quantity = models.PositiveIntegerField()
    # Pricing 
    price = models.DecimalField(max_digits=8, decimal_places=3)
    # Delivery 
    delivery_method = models.CharField(max_length=20, default="pickup")
    delivery_notes = models.TextField(blank=True)

    # Accounting etc
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)

    # Sustainability
    food_miles = models.FloatField(null=True, blank=True)

    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)

    STATUS_PENDING = "pending"
    STATUS_SHIPPED = "shipped"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SHIPPED, "Shipped"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    delivery_time = models.DateTimeField(null=True, blank=True)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

class RecurringOrder(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()  # 0 = Monday
    delivery_day_offset = models.IntegerField(default=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class RecurringOrderItem(models.Model):
    recurring_order = models.ForeignKey(RecurringOrder, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()

class Payment(models.Model):
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    orders = models.ManyToManyField(OrderItem)
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment to {self.producer} - {self.amount}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()

    content = models.ForeignKey(
        "products.EducationalContent",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    notification_type = models.CharField(
        max_length=20,
        choices=[
            ("normal", "Normal"),
            ("order", "Order Update"),
            ("alert", "Safety Alert"),
            ("discount", "Discount"),
        ],
        default="normal"
    )

    severity = models.CharField(
        max_length=10,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="low"
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Settlement(models.Model):
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    gross_sales = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    net_earnings = models.DecimalField(max_digits=10, decimal_places=2)
    items = models.ManyToManyField(OrderItem)