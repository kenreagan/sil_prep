from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Avg, Count, Q, Sum
from django.core.mail import send_mail
from django.conf import settings
import requests
import logging
from django.contrib.auth import authenticate
from .models import Customer, Category, Product, Order, OrderItem
from .serializers import (
    CustomerRegistrationSerializer, CustomerSerializer,
    CategorySerializer, ProductSerializer, ProductCreateSerializer,
    OrderSerializer, OrderCreateSerializer, CategoryAverageSerializer
)
from rest_framework.authtoken.models import Token
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

# OpenID Connect Configuration
class OpenIDConnect:
    @staticmethod
    def get_token():
        """Get OAuth2 token from provider"""
        client_id = settings.OIDC_CLIENT_ID
        client_secret = settings.OIDC_CLIENT_SECRET
        token_url = settings.OIDC_TOKEN_URL
        
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret
        )
        return token

    @staticmethod
    def verify_token(token):
        """Verify token with OpenID provider"""
        introspect_url = settings.OIDC_INTROSPECT_URL
        client_id = settings.OIDC_CLIENT_ID
        client_secret = settings.OIDC_CLIENT_SECRET
        
        response = requests.post(
            introspect_url,
            data={
                'token': token,
                'client_id': client_id,
                'client_secret': client_secret
            }
        )
        return response.json().get('active', False)

class OpenIDConnectPermission(permissions.BasePermission):
    """Custom permission for OpenID Connect"""
    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        return OpenIDConnect.verify_token(token)

class CustomerRegistrationView(generics.CreateAPIView):
    """Customer registration endpoint"""
    queryset = Customer.objects.all()
    serializer_class = CustomerRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        
        return Response({
            'message': 'Customer registered successfully',
            'customer_id': customer.id
        }, status=status.HTTP_201_CREATED)

class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Customer profile endpoint"""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

    def get_object(self):
        return self.request.user

class CategoryListCreateView(generics.ListCreateAPIView):
    """List and create categories"""
    queryset = Category.objects.filter(is_active=True).order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent', None)
        
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        elif parent_id is None and 'parent' not in self.request.query_params:
            queryset = queryset.filter(parent__isnull=True)
        
        return queryset

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Category detail endpoint"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

class ProductListCreateView(generics.ListCreateAPIView):
    """List and create products"""
    queryset = Product.objects.filter(is_active=True).select_related('category')
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category', None)
        search = self.request.query_params.get('search', None)
        
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                descendant_categories = [category] + category.get_descendants()
                queryset = queryset.filter(category__in=descendant_categories)
            except Category.DoesNotExist:
                queryset = queryset.none()
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )
        
        return queryset.order_by('name')

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Product detail endpoint"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

@api_view(['GET'])
@permission_classes([IsAuthenticated | OpenIDConnectPermission])
def category_average_price(request, category_id):
    """Get average price for products in a category and its subcategories"""
    try:
        category = Category.objects.get(id=category_id, is_active=True)
    except Category.DoesNotExist:
        return Response(
            {'error': 'Category not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    descendant_categories = [category] + category.get_descendants()
    products = Product.objects.filter(
        category__in=descendant_categories,
        is_active=True
    )
    
    if not products.exists():
        return Response({
            'category_id': category.id,
            'category_name': category.name,
            'average_price': None,
            'product_count': 0,
            'message': 'No products found in this category'
        })
    
    stats = products.aggregate(
        average_price=Avg('price'),
        product_count=Count('id'),
        total_value=Sum('price')
    )
    
    serializer = CategoryAverageSerializer({
        'category_id': category.id,
        'category_name': category.name,
        'average_price': stats['average_price'],
        'product_count': stats['product_count'],
        'total_value': stats['total_value']
    })
    
    return Response(serializer.data)

class OrderListCreateView(generics.ListCreateAPIView):
    """List and create orders"""
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        order_items_data = self.request.data.get('items', [])
        
        # Calculate total amount
        total_amount = 0
        items = []
        for item_data in order_items_data:
            product = get_object_or_404(Product, id=item_data['product_id'], is_active=True)
            quantity = item_data['quantity']
            item_total = product.price * quantity
            total_amount += item_total
            
            items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': product.price,
                'total_price': item_total
            })
        
        # Create order
        order = serializer.save(
            customer=self.request.user,
            total_amount=total_amount,
            shipping_address=self.request.data.get('shipping_address', '')
        )
        
        # Create order items
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['total_price']
            )
        
        # Send notifications
        self.send_customer_sms(order)
        self.send_admin_email(order)

    def send_customer_sms(self, order):
        """Send SMS notification to customer using Africa's Talking"""
        if not order.customer.phone_number:
            logger.warning(f"No phone number for customer {order.customer.email}")
            return

        message = f"Hi {order.customer.first_name}, your order {order.order_number} " \
                 f"totaling KES {order.total_amount} has been placed successfully. " \
                 f"Thank you for shopping with us!"

        try:
            api_key = getattr(settings, 'AFRICAS_TALKING_API_KEY', '')
            username = getattr(settings, 'AFRICAS_TALKING_USERNAME', 'sandbox')
            
            if api_key:
                url = 'https://api.sandbox.africastalking.com/version1/messaging'
                headers = {
                    'apiKey': api_key,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                data = {
                    'username': username,
                    'to': order.customer.phone_number,
                    'message': message
                }
                
                response = requests.post(url, headers=headers, data=data)
                if response.status_code == 201:
                    logger.info(f"SMS sent successfully for order {order.order_number}")
                else:
                    logger.error(f"Failed to send SMS for order {order.order_number}: {response.text}")
            else:
                logger.info(f"SMS would be sent to {order.customer.phone_number}: {message}")
                
        except Exception as e:
            logger.error(f"Error sending SMS for order {order.order_number}: {str(e)}")

    def send_admin_email(self, order):
        """Send email notification to admin"""
        try:
            subject = f"New Order Placed - {order.order_number}"
            
            items_details = []
            for item in order.items.all():
                items_details.append(
                    f"- {item.product.name} (SKU: {item.product.sku}) "
                    f"x {item.quantity} @ KES {item.unit_price} = KES {item.total_price}"
                )
            
            message = f"""
A new order has been placed:

Order Number: {order.order_number}
Customer: {order.customer.first_name} {order.customer.last_name}
Email: {order.customer.email}
Phone: {order.customer.phone_number or 'Not provided'}
Total Amount: KES {order.total_amount}
Status: {order.get_status_display()}

Shipping Address:
{order.shipping_address}

Order Items:
{chr(10).join(items_details)}

Notes: {order.notes or 'None'}

Order placed on: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()

            admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[admin_email],
                fail_silently=False
            )
            
            logger.info(f"Admin email sent for order {order.order_number}")
            
        except Exception as e:
            logger.error(f"Error sending admin email for order {order.order_number}: {str(e)}")

class OrderDetailView(generics.RetrieveAPIView):
    """Order detail endpoint"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated | OpenIDConnectPermission]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated | OpenIDConnectPermission])
def order_statistics(request):
    """Get order statistics for the authenticated customer"""
    customer = request.user
    orders = Order.objects.filter(customer=customer)
    
    stats = {
        'total_orders': orders.count(),
        'total_spent': sum(order.total_amount for order in orders),
        'orders_by_status': {}
    }
    
    for status_code, status_name in Order.STATUS_CHOICES:
        count = orders.filter(status=status_code).count()
        stats['orders_by_status'][status_name] = count
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([IsAuthenticated | OpenIDConnectPermission])
def category_tree(request):
    """Get complete category tree"""
    def build_tree(parent=None):
        categories = Category.objects.filter(
            parent=parent, 
            is_active=True
        ).order_by('name')
        
        tree = []
        for category in categories:
            node = {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'level': category.level,
                'children': build_tree(category)
            }
            tree.append(node)
        return tree
    
    return Response(build_tree())

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint that returns authentication token"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Username and password required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
    else:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def oidc_login(request):
    """OpenID Connect login endpoint"""
    token = OpenIDConnect.get_token()
    return Response({
        'access_token': token['access_token'],
        'token_type': token['token_type'],
        'expires_in': token['expires_in']
    })