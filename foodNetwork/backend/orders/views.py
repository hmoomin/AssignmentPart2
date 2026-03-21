from urllib import request
from django.shortcuts import render
from rest_framework import generics
from .serializers import CartItemSerializer, OrderItemSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Cart, Order, OrderItem, CartItem
from users.models import User
from .utils import calculate_distance
from rest_framework.exceptions import ValidationError
from products.models import Product, EducationalContent
from products.serializers import ProductSerializer
from django.db.models import Avg, Sum, Count
from rest_framework.permissions import IsAdminUser
from .serializers import OrderItemSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import datetime, timedelta

class CheckoutView(APIView):

    def post(self, request):
        user = request.user
        cart = Cart.objects.get(user=user)

        delivery_date = request.data.get("delivery_date")

        if not delivery_date:
            raise ValidationError("Delivery date required")

        delivery_date = datetime.fromisoformat(delivery_date)

        if delivery_date < timezone.now() + timedelta(hours=48):
            raise ValidationError("Minimum 48-hour notice required")

        order = Order.objects.create(
            customer=user,
            delivery_date=delivery_date
        )

        for item in cart.items.all():
            product = item.product

            if not product.is_available():
                raise ValidationError(f"{product.name} is not available")

            if product.stock_quantity < item.quantity:
                raise ValidationError(f"Not enough stock for {product.name}")

            product.stock_quantity -= item.quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                producer=product.producer,
                quantity=item.quantity,
                price=product.discounted_price()
            )

        cart.items.all().delete()

        return Response({"message": "Order placed successfully"})


class CartItemCreateView(generics.CreateAPIView):

    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer


class CartItemListView(generics.ListAPIView):

    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer

class ProducerOrdersView(APIView):

    def get(self, request):

        producer = request.user

        orders = OrderItem.objects.filter(
            producer=producer
        )

        serializer = OrderItemSerializer(orders, many=True)

        return Response(serializer.data)
    
class CustomerDashboardView(APIView):

    def get(self, request):

        user = request.user

        cart, created = Cart.objects.get_or_create(user=user)

        cart_items = cart.items.all()
        orders = Order.objects.filter(customer=user)

        cart_data = CartItemSerializer(cart_items, many=True).data
        order_data = OrderItemSerializer(
            OrderItem.objects.filter(order__customer=user),
            many=True
        ).data

        return Response({
            "cart_items": cart_data,
            "orders": order_data
        })
    
class ProducerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        producer = request.user

        if not producer.is_producer:
            return Response({"error": "Not allowed"}, status=403)

        products = Product.objects.filter(producer=producer)
        orders = OrderItem.objects.filter(producer=producer)

        return Response({
            "products": ProductSerializer(products, many=True).data,
            "orders": OrderItemSerializer(orders, many=True).data,
            "total_sales": sum(o.price * o.quantity for o in orders)
        })
    
class SustainabilityReportView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request):

        order_items = OrderItem.objects.all()

        total_food_miles = order_items.aggregate(
            Sum("food_miles")
        )["food_miles__sum"] or 0

        avg_food_miles = order_items.aggregate(
            Avg("food_miles")
        )["food_miles__avg"] or 0

        total_orders = Order.objects.count()

        local_items = order_items.filter(food_miles__lte=50).count()
        non_local_items = order_items.filter(food_miles__gt=50).count()

        return Response({
            "total_orders": total_orders,
            "total_food_miles": total_food_miles,
            "average_food_miles": avg_food_miles,
            "local_products": local_items,
            "non_local_products": non_local_items
        })
    
class CustomerDashboardView(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        if user.is_producer:
            return Response(
                {"error": "Producers cannot access the customer dashboard"},
                status=403
            )

        cart, created = Cart.objects.get_or_create(user=user)

        cart_items = cart.items.all()
        orders = OrderItem.objects.filter(order__customer=user)

        cart_data = CartItemSerializer(cart_items, many=True).data
        order_data = OrderItemSerializer(orders, many=True).data

        return Response({
            "cart_items": cart_data,
            "orders": order_data
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
    
def producer_dashboard_page(request):
    return render(request, "dashboards/producerDash.html")


def customer_dashboard_page(request):
    return render(request, "dashboards/customerDash.html")

def add_product_page(request):
    return render(request, "dashboards/addProduct.html")

def add_education_page(request):
    return render(request, "dashboards/addEducation.html")

def edit_product_page(request, pk):
    product = get_object_or_404(Product, pk=pk, producer=request.user)
    return render(request, "dashboards/editProducts.html", {"product": product})

def delete_product_page(request, pk):
    product = get_object_or_404(Product, pk=pk, producer=request.user)

    if request.method == "POST":
        product.delete()
        return redirect("/api/orders/dashboard/producer/view/")

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