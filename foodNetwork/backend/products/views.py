from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Product, EducationalContent
from .serializers import ProductSerializer, EducationalContentSerializer
from orders.utils import calculate_distance


# ================= PRODUCTS ================= #

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return products for logged-in producer
        return Product.objects.filter(producer=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_producer:
            raise PermissionDenied("Only producers can create products")
        serializer.save(producer=self.request.user)


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


class EducationalContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EducationalContentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EducationalContent.objects.filter(
            producer=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()