from itertools import product
from urllib import request
from django.shortcuts import render
from rest_framework import generics
from .serializers import CartItemSerializer, OrderItemSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Cart, Order, OrderItem, CartItem, Notification, RecurringOrderItem, RecurringOrder
from users.models import User
from products.utils import calculate_distance, postcode_to_coords
from rest_framework.exceptions import ValidationError
from products.models import Product, EducationalContent
from products.serializers import ProductSerializer
from django.db.models import Avg, Sum, Count
from rest_framework.permissions import IsAdminUser
from .serializers import OrderItemSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from collections import defaultdict
from .models import OrderItem
import stripe
from django.conf import settings
from django.utils.timezone import make_aware, is_naive
from decimal import Decimal
import csv
from django.http import HttpResponse


stripe.api_key = settings.STRIPE_SECRET_KEY

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    @transaction.atomic
    def post(self, request):
        user = request.user
        cart = Cart.objects.filter(user=user).first()

        if user.is_community_group:
            for item in cart.items.all():
                if item.quantity > 100: 
                    raise ValidationError("Bulk quantity exceeds allowed limit for this product")

        if not cart or not cart.items.exists():
            raise ValidationError("Cart is empty")
        delivery_method = request.data.get("delivery_method")
        address_line = request.data.get("address_line")
        postcode = request.data.get("postcode")
        delivery_date = request.data.get("delivery_date")
        # VALIDATION
        if delivery_method == "delivery":
            if not address_line or not postcode:
                raise ValidationError("Address and postcode required for delivery")
        if not delivery_date:
            raise ValidationError("Delivery date required")
        delivery_date = parse_datetime(delivery_date)
        if not delivery_date:
            raise ValidationError("Invalid delivery date format")
        if is_naive(delivery_date):
            delivery_date = make_aware(delivery_date)
        if delivery_date <= timezone.now() + timedelta(hours=48):
            raise ValidationError("Orders must be placed at least 48 hours in advance")
        
        is_bulk = request.data.get("is_bulk_order", False)
        instructions = request.data.get("instructions", "")
        # CREATE ORDER
        order = Order.objects.create(
            customer=user,
            delivery_date=delivery_date,
            status="pending",
            payment_status="processing",
            is_bulk_order=is_bulk,
            special_instructions=instructions
        )
        created_items = []
        for item in cart.items.all():
            product = item.product
            if not product.is_active:
                raise ValidationError(f"{product.name} has been recalled and cannot be ordered")
            if product.stock_quantity < item.quantity:
                raise ValidationError(f"Not enough stock for {product.name}")
            producer = product.producer

            # FOOD MILES CALC
            customer_postcode = user.postcode
            producer_postcode = producer.postcode
            lat1, lon1 = postcode_to_coords(customer_postcode)
            lat2, lon2 = postcode_to_coords(producer_postcode)
            if None not in (lat1, lon1, lat2, lon2):
                food_miles = calculate_distance(lat1, lon1, lat2, lon2)
            else:
                food_miles = None
            # STOCK UPDATE
            product.stock_quantity -= item.quantity
            product.save()
            # STORE ADDRESS CLEANLY
            full_address = (
                f"{address_line}, {postcode}"
                if delivery_method == "delivery"
                else ""
            )
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                producer=producer,
                producer_name=producer.username,
                quantity=item.quantity,
                price=product.discounted_price,
                delivery_method=delivery_method,
                delivery_notes=full_address,
                food_miles=food_miles,
                contact_name=user.contact_name or user.username,
                contact_phone=user.phone or "",
                contact_email=user.email or ""
            )
            created_items.append(order_item)
            # NOTIFICATION
            message = f"New order: {product.name} x {item.quantity}"

            if is_bulk:
                message = f"📦 BULK ORDER: {product.name} x {item.quantity}"

            if instructions:
                message += f" | Notes: {instructions}"

            Notification.objects.create(
                user=producer,
                message=message,
                notification_type="order"
            )
        # PAYMENT
        total_amount = sum(item.price * item.quantity for item in created_items)
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount * 100),
            currency="gbp",
            automatic_payment_methods={"enabled": True},
            metadata={"order_id": order.id}
        )
        # CLEAR CART
        cart.items.all().delete()
        return Response({
            "client_secret": intent.client_secret,
            "order_id": order.id,
            "amount": float(total_amount)
        })
    
class ProducerNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user,
        ).order_by("-created_at")

        return Response([
            {
                "id": n.id,
                "message": n.message,
                "created_at": n.created_at,
                "is_read": n.is_read,
                "notification_type": n.notification_type,
                "severity": n.severity
            } for n in notifications
        ])
    
class CustomerNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user

        ).order_by("-created_at")

        return Response([
            {
                "id": n.id,
                "message": n.message,
                "created_at": n.created_at,
                "is_read": n.is_read,
                "notification_type": n.notification_type,
                "severity": n.severity,
                "content_id": n.content.id if n.content else None
            }
            for n in notifications
        ])
    
class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user
        )

        notification.is_read = True
        notification.save()

        return Response({"message": "Marked as read"})

class SafetyAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.is_producer:
            raise ValidationError("Only producers can send alerts")

        product_id = request.data.get("product_id")
        message = request.data.get("message")
        severity = request.data.get("severity", "high")

        if not product_id or not message:
            raise ValidationError("Product and message required")

        # GET PRODUCT (IMPORTANT)
        product = get_object_or_404(Product, id=product_id, producer=user)

        severity = request.data.get("severity", "low")

        # AUTO RECALL FOR HIGH / CRITICAL
        if severity in ["high", "critical"]:
            product.status = "recalled"
            product.save()
        # PRODUCT RECALL (AUTO DISABLE)
        product.is_active = False
        product.save()

        # FIND AFFECTED CUSTOMERS
        affected_orders = OrderItem.objects.filter(
            product_id=product_id
        ).select_related("order")

        customers = set(item.order.customer for item in affected_orders)

        # SEND ALERTS
        for customer in customers:
            Notification.objects.create(
                user=customer,
                message=f"⚠️ SAFETY ALERT ({severity.upper()}): {product.name} - {message}",
                notification_type="alert",
                severity=severity
            )

        return Response({
            "message": "Alert sent & product recalled",
            "product_disabled": True
        })

class ResolveProductView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk, producer=request.user)

        product.is_active = True
        product.is_recalled = False
        product.status = "active"
        product.save()

        return Response({"message": "Product reactivated"})
    
class DisableProductView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk, producer=request.user)

        product.is_active = False
        product.is_recalled = True
        product.status = "disabled"
        product.save()

        return Response({"message": "Product disabled"})

class ConfirmPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        order.payment_status = "paid"
        order.paid_at = timezone.now()
        order.save()

        return Response({"message": "Payment confirmed"})

class CartItemCreateView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)

        existing_item = CartItem.objects.filter(
            cart=cart,
            product=product
        ).first()

        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            self.instance = existing_item
        else:
            self.instance = serializer.save(cart=cart)

        if product.is_recalled:
            raise ValidationError("This product has been recalled")

class CartItemListView(generics.ListAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)
    
class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        change = int(request.data.get("change", 0))

        new_quantity = item.quantity + change

        # STOCK VALIDATION
        if new_quantity > item.product.stock_quantity:
            raise ValidationError("Not enough stock available")

        item.quantity = new_quantity

        if item.quantity <= 0:
            item.delete()
            return Response({"message": "Item removed"})

        item.save()
        return Response({"quantity": item.quantity})

    def delete(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        item.delete()
        return Response({"message": "Deleted"})

class ReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        added = []
        failed = []
        now = timezone.now().date()
        
        for item in order.items.all():

            # product deleted
            if not item.product:
                failed.append({
                    "product": item.product_name,
                    "reason": "Product no longer exists"
                })
                continue

            # expiry check
            if item.product.best_before_date and item.product.best_before_date < now:
                failed.append({
                    "product": item.product.name,
                    "reason": "Product has expired"
                })
                continue

            # out of stock
            if item.product.stock_quantity <= 0:
                failed.append({
                    "product": item.product.name,
                    "reason": "Out of stock"
                })
                continue

            # add to cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=item.product,
                defaults={"quantity": item.quantity}
            )

            if not created:
                cart_item.quantity += item.quantity
                cart_item.save()

            added.append(item.product.name)

        return Response({
            "message": "Reorder complete",
            "added": added,
            "failed": failed
        })
    
class CreateRecurringOrderView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        cart = Cart.objects.filter(user=user).first()
        if not cart or not cart.items.exists():
            raise ValidationError("Cart is empty")
        recurring = RecurringOrder.objects.create(
            customer=user,
            day_of_week=request.data.get("day_of_week"),
            delivery_day_offset=request.data.get("delivery_offset", 2)
        )
        for item in cart.items.all():
            RecurringOrderItem.objects.create(
                recurring_order=recurring,
                product=item.product,
                quantity=item.quantity
            )
        return Response({"message": "Recurring order created"})

class UpdateOrderItemView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        item = get_object_or_404(OrderItem, pk=pk, producer=request.user)

        VALID_TRANSITIONS = {
            "pending": ["shipped", "ready"],
            "shipped": ["completed"],
            "ready": ["completed"],
            "completed": []
        }

        new_status = request.data.get("status")

        if new_status:
            if new_status not in VALID_TRANSITIONS[item.status]:
                raise ValidationError("Invalid status transition")

            item.status = new_status

            # CREATE CUSTOMER NOTIFICATION
            message = None

            if new_status == "ready":
                message = f"Order #{item.order.id}: {item.product_name} is ready for pickup"

            elif new_status == "shipped":
                message = f"Order #{item.order.id}: {item.product_name} has been shipped"

            elif new_status == "completed":
                message = f"Order #{item.order.id}: {item.product_name} order completed"

            if message:
                Notification.objects.create(
                    user=item.order.customer,
                    message=message
                )

        delivery_time = request.data.get("delivery_time")
        if delivery_time:
            item.delivery_time = delivery_time
            Notification.objects.create(
                user=item.order.customer,
                message=f"Order #{item.order.id}: Delivery scheduled for {delivery_time}"
            )

        item.save()

        return Response({"message": "Updated"})

class ProducerOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        producer = request.user
        items = OrderItem.objects.filter(
            producer=producer
        ).select_related("order", "order__customer")

        grouped = {}
        total_sales = 0

        for item in items:
            order_id = item.order.id

            if order_id not in grouped:
                grouped[order_id] = {
                    "date": item.order.created_at,
                    "customer_name": item.contact_name,
                    "customer_phone": item.contact_phone,
                    "customer_email": item.contact_email,
                    "items": [],
                    "total": 0
                }

            subtotal = float(item.price * item.quantity)

            grouped[order_id]["items"].append({
                "id": item.id,
                "product": item.product_name,
                "quantity": item.quantity,
                "status": item.status,
                "delivery_time": item.delivery_time.isoformat() if item.delivery_time else None,
                "delivery_method": item.delivery_method,
                "delivery_notes": item.delivery_notes,
                "customer_name": item.contact_name,
                "customer_phone": item.contact_phone,
                "customer_email": item.contact_email,
                "subtotal": subtotal
            })

            grouped[order_id]["total"] += subtotal
            if item.order.payment_status == "paid":
                total_sales += subtotal

        return Response({
            "orders": grouped,
            "total_sales": total_sales,
            "network_fee": total_sales * 0.05,
            "net_earnings": total_sales * 0.95
        })

class WeeklySettlementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.is_producer:
            return Response({"error": "Only producers allowed"}, status=403)

        with transaction.atomic():
            items = OrderItem.objects.select_for_update().filter(
                producer=user,
                order__payment_status="paid",
                is_settled=False
            )

            if not items.exists():
                return Response({
                    "status": "No settlements available",
                    "period": "Unsettled Paid Orders",
                    "gross_sales": 0,
                    "platform_fee": 0,
                    "net_earnings": 0,
                    "tax_year_total": float(sum(
                        i.price * i.quantity
                        for i in OrderItem.objects.filter(
                            producer=user,
                            order__payment_status="paid"
                        )
                    )),
                    "items_count": 0,
                    "breakdown": []
                })

            total = sum(item.price * item.quantity for item in items)
            fee = total * Decimal("0.05")
            net = total - fee

            breakdown = [
                {
                    "order_id": item.order.id,
                    "product": item.product_name,
                    "quantity": item.quantity,
                    "subtotal": float(item.price * item.quantity),
                }
                for item in items
            ]
            # mark as settled
            now = timezone.now()
            for item in items:
                item.is_settled = True
                item.settled_at = now

            OrderItem.objects.bulk_update(items, ["is_settled", "settled_at"])

            tax_year_total = sum(
                i.price * i.quantity
                for i in OrderItem.objects.filter(
                    producer=user,
                    order__payment_status="paid"
                )
            )

            return Response({
                "status": "Processed",
                "period": "Unsettled Paid Orders",
                "gross_sales": float(total),
                "platform_fee": float(fee),
                "net_earnings": float(net),
                "tax_year_total": float(tax_year_total),
                "items_count": len(items),
                "breakdown": breakdown
            })

class EnvironmentalReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, order_id):
        user = request.user
        try:
            order = Order.objects.get(id=order_id, customer=user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        items = OrderItem.objects.filter(order=order)

        report = []
        total_miles = 0

        for item in items:
            product = item.product
            producer = product.producer
            if (
                producer.latitude is not None and
                producer.longitude is not None and
                user.latitude is not None and
                user.longitude is not None
            ):
                miles = calculate_distance(
                    producer.latitude,
                    producer.longitude,
                    user.latitude,
                    user.longitude
                )
            else:
                miles = 0

            total_miles += miles

            report.append({
                "product": product.name,
                "quantity": item.quantity,
                "food_miles": round(miles, 2),
                "subtotal": float(item.subtotal())
            })

        # CO2 calculation
        CO2_PER_MILE = 0.411
        total_co2 = total_miles * CO2_PER_MILE

        # --- CSV RESPONSE ---
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="report_order_{order.id}.csv"'

        writer = csv.writer(response)

        writer.writerow(["Product", "Quantity", "Food Miles", "Subtotal (£)"])

        for item in report:
            writer.writerow([
                item["product"],
                item["quantity"],
                item["food_miles"],
                item["subtotal"]
            ])
        writer.writerow([])
        writer.writerow(["TOTAL MILES", round(total_miles, 2)])
        writer.writerow(["TOTAL CO2 (kg)", round(total_co2, 2)])
        return response
    
class ShareEducationalContentView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        user = request.user
        if not user.is_producer:
            raise ValidationError("Only producers can share content")
        content = get_object_or_404(
            EducationalContent,
            pk=pk,
            producer=user
        )
        # Get all customers (who have ordered from this producer)
        customers = set(
            item.order.customer
            for item in OrderItem.objects.filter(producer=user)
        )
        for customer in customers:
            Notification.objects.create(
                user=customer,
                message=f"📢 New {content.content_type.title()} added: {content.title}",
                notification_type="normal",
                content=content 
            )
        return Response({"message": "Content shared successfully"})
    
class CustomerDashboardView(APIView):
    def get(self, request):
        user = request.user
        cart, _ = Cart.objects.get_or_create(user=user)
        cart_items = cart.items.all()
        orders = OrderItem.objects.filter(order__customer=user)

        cart_total = sum(
            item.product.discounted_price * item.quantity
            for item in cart_items
        )

        return Response({
            "cart_items": CartItemSerializer(cart_items, many=True).data,
            "cart_total": cart_total,
            "orders": OrderItemSerializer(orders, many=True).data
        })


class ProducerDashboardView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        producer = request.user
        if not producer.is_producer:
            return Response(
                {"error": "Only producers can access this dashboard"},
                status=403
            )

        products = Product.objects.filter(producer=producer)
        print("USER:", request.user)
        print("IS PRODUCER:", request.user.is_producer)
        orders = OrderItem.objects.filter(producer=producer)

        product_data = ProductSerializer(products, many=True).data
        order_data = OrderItemSerializer(orders, many=True).data

        total_sales = sum(
            item.price * item.quantity for item in orders
        )

        return Response({
            "products": product_data,
            "orders": order_data,
            "total_sales": total_sales
        })
    
@login_required
def producer_dashboard_page(request):
    if not request.user.is_producer:
        return redirect("/login/")
    return render(request, "dashboards/producerDash.html")

@login_required
def customer_dashboard_page(request):
    if request.user.is_producer:
        return redirect("/api/orders/dashboard/producer/view/")
    return render(request, "dashboards/customerDash.html")

@login_required
def add_product_page(request):
    if not request.user.is_producer:
        return redirect("/login/")
    return render(request, "dashboards/addProduct.html")

@login_required
def add_education_page(request):
    if not request.user.is_producer:
        return redirect("/login/")
    return render(request, "dashboards/addEducation.html")

@login_required
def edit_product_page(request, pk):
    if not request.user.is_producer:
        return redirect("/login/")
    product = get_object_or_404(Product, pk=pk, producer=request.user)
    return render(request, "dashboards/editProducts.html", {"product": product})

@login_required
def delete_product_page(request, pk):
    if not request.user.is_producer:
        return redirect("/login/")
    product = get_object_or_404(Product, pk=pk, producer=request.user)
    return render(request, "dashboards/deleteProducts.html", {"product": product})

def edit_education_page(request, pk):
    content = get_object_or_404(EducationalContent, pk=pk, producer=request.user)
    return render(request, "dashboards/editEducation.html", {"content": content})

def delete_education_page(request, pk):
    content = get_object_or_404(EducationalContent, pk=pk, producer=request.user)
    if request.method == "POST":
        content.delete()
        return redirect("/api/orders/dashboard/producer/view/")
    return render(request, "dashboards/deleteEducation.html", {"content": content})