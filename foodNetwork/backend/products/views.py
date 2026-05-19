from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product, EducationalContent, Review
from .serializers import ProductSerializer, EducationalContentSerializer
from rest_framework import viewsets
from django.utils import timezone
from .utils import calculate_distance, postcode_to_coords
from datetime import timedelta
from django.db.models import Q
from users.models import User
from django.db.models import F, ExpressionWrapper, DecimalField
from orders.models import OrderItem
from django.shortcuts import render
from django.shortcuts import get_object_or_404

# ================= PRODUCTS ================= #
class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Product.objects.filter(
            is_active=True,
            is_recalled=False,
            stock_quantity__gt=0
        ).select_related("producer")

        # ------------------------
        # FILTERS
        # ------------------------
        category = self.request.query_params.get("category")
        search = self.request.query_params.get("search")
        producer = self.request.query_params.get("producer")
        organic = self.request.query_params.get("organic")
        max_distance = self.request.query_params.get("max_distance")

        if category:
            queryset = queryset.filter(category=category)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(origin_farm__icontains=search) |
                Q(producer__username__icontains=search)|
                Q(is_organic__icontains=search)|
                Q(category__icontains=search)
            )

        if producer:
            queryset = queryset.filter(producer__username=producer)

        if organic == "true":
            queryset = queryset.filter(is_organic=True)

        if max_distance:
            max_distance = float(max_distance)

        # ------------------------
        # ANNOTATIONS
        # ------------------------
        queryset = queryset.annotate(
            discounted_price_calc=ExpressionWrapper(
                F("price") * (1 - F("discount") / 100),
                output_field=DecimalField()
            ),
            discount_amount=ExpressionWrapper(
                F("price") * F("discount") / 100,
                output_field=DecimalField()
            )
        )

        # ------------------------
        # SORTING
        # ------------------------
        ordering = self.request.query_params.get("ordering")

        if ordering == "price_asc":
            queryset = queryset.order_by("discounted_price_calc")
        elif ordering == "price_desc":
            queryset = queryset.order_by("-discounted_price_calc")
        elif ordering == "newest":
            queryset = queryset.order_by("-created_at")
        elif ordering == "discount":
            queryset = queryset.order_by("-discount_amount")
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        user = request.user
        max_distance = request.query_params.get("max_distance")
        today = timezone.now().date()

        # expiry logic
        expiring_products = queryset.filter(
            best_before_date__isnull=False,
            best_before_date__lte=today + timedelta(days=2)
        )
        for product in expiring_products:
            product.auto_apply_expiry_discount()

        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        for i, product in enumerate(queryset):
            has_purchased = OrderItem.objects.filter(
                order__customer=request.user,
                product=product
            ).exists()
            data[i]["has_purchased"] = has_purchased

        expired_products = queryset.filter(
            best_before_date__lt=today,
            is_active=True
        )

        for product in expired_products:
            product.handle_expiry()

        # USE STORED COORDINATES
        filtered_data = []

        for i, product in enumerate(queryset):
            producer = product.producer
            if (
                producer.latitude is not None and
                producer.longitude is not None and
                user.latitude is not None and
                user.longitude is not None
            ):
                distance = calculate_distance(
                    producer.latitude,
                    producer.longitude,
                    user.latitude,
                    user.longitude
                )
                if max_distance and float(distance) > float(max_distance):
                    continue  # skip product
                data[i]["food_miles"] = round(distance, 2)
            else:
                data[i]["food_miles"] = None
            filtered_data.append(data[i])
        return Response(filtered_data)

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(producer=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_producer:
            raise PermissionDenied("Only producers can create products")
        serializer.save(
            producer=self.request.user,
            origin_farm=self.request.data.get("origin_farm") or self.request.user.username
        )

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Restrict access to own products only
        return Product.objects.filter(producer=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

# ================= REVIEWS ================= #

class CreateReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product")
        rating = request.data.get("rating")
        comment = request.data.get("comment", "")
        anonymous = request.data.get("anonymous", False)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        # must have ordered
        has_ordered = OrderItem.objects.filter(
            order__customer=request.user,
            product=product
        ).exists()
        if not has_ordered:
            return Response({
                "error": "You can only review products you have purchased"
            }, status=403)
        # prevent duplicate reviews
        if Review.objects.filter(user=request.user, product=product).exists():
            return Response({
                "error": "You already reviewed this product"
            }, status=400)
        review = Review.objects.create(
            user=request.user,
            product=product,
            rating=rating,
            comment=comment,
            anonymous=anonymous
        )
        return Response({"message": "Review created"})
    
class ProductReviewListView(APIView):
    def get(self, request, product_id):
        reviews = Review.objects.filter(product_id=product_id)

        data = []
        for r in reviews:
            data.append({
                "rating": r.rating,
                "comment": r.comment,
                "user": "Anonymous" if r.anonymous else r.user.username,
                "created_at": r.created_at
            })

        return Response(data)
    
def review_page(request):
    return render(request, "dashboards/review.html")

# ================= LOCAL PRODUCTS ================= #

class LocalProductsView(APIView):

    def get(self, request):
        user = request.user
        products = Product.objects.all()
        product_distances = []

        for product in products:
            producer = product.producer
            if (
                producer.latitude is not None
                and producer.longitude is not None
                and user.latitude is not None
                and user.longitude is not None
            ):
                distance = calculate_distance(
                    producer.latitude,
                    producer.longitude,
                    user.latitude,
                    user.longitude
                )
            else:
                distance = None
            product_distances.append((product, distance))

        product_distances.sort(key=lambda x: x[1] if x[1] else 999999)
        sorted_products = [p[0] for p in product_distances]

        serializer = ProductSerializer(sorted_products, many=True)
        return Response(serializer.data)


# ================= SEARCH ================= #

class ProductSearchView(APIView):
    def get(self, request):
        query = request.GET.get("q", "")
        products = Product.objects.filter(name__icontains=query)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

class ProductFilterOptionsView(APIView):
    def get(self, request):
        # Clean category choices
        categories = [
            {"value": c[0], "label": c[1]}
            for c in Product.CATEGORY_CHOICES
            if c[0]  # filter out empty keys
        ]
        # Distinct producers WITH products
        producers = (
            User.objects
            .filter(product__isnull=False)
            .exclude(username__isnull=True)
            .exclude(username__exact="")
            .values("username")
            .distinct()
        )
        return Response({
            "categories": categories,
            "producers": list(producers)
        })

# ================= EDUCATIONAL CONTENT ================= #

class EducationalContentListCreateView(generics.ListCreateAPIView):
    serializer_class = EducationalContentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EducationalContent.objects.filter(
            producer=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(producer=self.request.user)


class EducationalContentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        content = get_object_or_404(
            EducationalContent,
            pk=pk,
            producer__in=User.objects.filter(
                orderitem__order__customer=request.user
            )
        )

        serializer = EducationalContentSerializer(content)
        return Response(serializer.data)

class EducationalContentListView(generics.ListAPIView):
    serializer_class = EducationalContentSerializer
    def get_queryset(self):
        queryset = EducationalContent.objects.all()
        content_type = self.request.query_params.get("type")
        producer = self.request.query_params.get("producer")

        if content_type:
            queryset = queryset.filter(content_type=content_type)
        if producer:
            queryset = queryset.filter(producer__username=producer)
        return queryset.order_by("-created_at")