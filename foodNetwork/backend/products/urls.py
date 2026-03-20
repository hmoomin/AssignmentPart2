from django.urls import path
from .views import (ProductListCreateView, ProductDetailView, LocalProductsView, ProductSearchView, EducationalContentListCreateView, EducationalContentDetailView,
)

urlpatterns = [
    # PRODUCTS
    path('', ProductListCreateView.as_view()),
    path('<int:pk>/', ProductDetailView.as_view()),
    # EXTRA FEATURES
    path('local/', LocalProductsView.as_view()),
    path('search/', ProductSearchView.as_view()),
    # EDUCATIONAL CONTENT
    path('education/', EducationalContentListCreateView.as_view()),
    path('education/<int:pk>/', EducationalContentDetailView.as_view()),
]