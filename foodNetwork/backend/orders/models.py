from django.db import models
from django.conf import settings
from products.models import Product
from django.utils import timezone
from datetime import timedelta
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user}'s cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.price * self.quantity

class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(default=timezone.now())

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
        return sum(item.price * item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    food_miles = models.FloatField(null=True, blank=True)


class Payment(models.Model):
    producer = models.ForeignKey(User, on_delete=models.CASCADE)
    orders = models.ManyToManyField(OrderItem)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


def send_urgent_alert(producer, content):
    customers = User.objects.filter(role="customer")

    for customer in customers:
        Message.objects.create(
            sender=producer,
            receiver=customer,
            content=content,
            is_urgent=True
        )

def generate_weekly_payments():
    last_week = timezone.now() - timedelta(days=7)

    producers = User.objects.filter(role="producer")

    for producer in producers:
        orders = OrderItem.objects.filter(
            producer=producer,
            order__created_at__gte=last_week
        )

        total = sum(o.price * o.quantity for o in orders)

        if total > 0:
            payment = Payment.objects.create(
                producer=producer,
                amount=total
            )
            payment.orders.set(orders)