from django.urls import path
from .views import (ProductListCreateView, ProductDetailView, LocalProductsView, ProductSearchView, EducationalContentListCreateView, EducationalContentDetailView, ProductListView, ProductFilterOptionsView, CreateReviewView, ProductReviewListView
)

urlpatterns = [
    # PRODUCTS
    path('', ProductListCreateView.as_view()), # producers
    path('list/', ProductListView.as_view()),  # customers
    path("filters/", ProductFilterOptionsView.as_view()),
    path('<int:pk>/', ProductDetailView.as_view()),
    # EXTRA FEATURES
    path('local/', LocalProductsView.as_view()),
    path('search/', ProductSearchView.as_view()),
    path("reviews/create/", CreateReviewView.as_view()),
    path("reviews/<int:product_id>/", ProductReviewListView.as_view()),
    # EDUCATIONAL CONTENT
    path('education/', EducationalContentListCreateView.as_view()),
    path('education/<int:pk>/', EducationalContentDetailView.as_view()),
]