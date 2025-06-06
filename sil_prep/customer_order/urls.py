from django.urls import path
from . import views

app_name = 'customer_order'

urlpatterns = [
    # Authentication
    path('auth/login/', views.login_view, name='login'),
    path('auth/oidc-login/', views.oidc_login, name='oidc-login'),
    
    # Customer Management
    path('customers/register/', views.CustomerRegistrationView.as_view(), name='customer-register'),
    path('customers/profile/', views.CustomerProfileView.as_view(), name='customer-profile'),
    
    # Categories
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<uuid:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<uuid:category_id>/average-price/', views.category_average_price, name='category-average-price'),
    path('categories/tree/', views.category_tree, name='category-tree'),
    
    # Products
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<uuid:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Orders
    path('orders/', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/statistics/', views.order_statistics, name='order-statistics'),
]