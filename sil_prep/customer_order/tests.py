from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from decimal import Decimal
import json

from .models import Customer, Category, Product, Order, OrderItem

User = get_user_model()


class CustomerModelTest(TestCase):
    """Test cases for Customer model"""
    
    def setUp(self):
        self.customer_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+254700000000',
            'password': 'testpassword123'
        }
    
    def test_create_customer(self):
        """Test customer creation"""
        customer = Customer.objects.create_user(**self.customer_data)
        self.assertEqual(customer.email, 'test@example.com')
        self.assertEqual(customer.username, 'testuser')
        self.assertTrue(customer.check_password('testpassword123'))
    
    def test_customer_str_representation(self):
        """Test customer string representation"""
        customer = Customer.objects.create_user(**self.customer_data)
        expected = "John Doe (test@example.com)"
        self.assertEqual(str(customer), expected)


class CategoryModelTest(TestCase):
    """Test cases for Category model"""
    
    def setUp(self):
        self.root_category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.child_category = Category.objects.create(
            name='Smartphones',
            slug='smartphones',
            parent=self.root_category
        )
        self.grandchild_category = Category.objects.create(
            name='Android Phones',
            slug='android-phones',
            parent=self.child_category
        )
    
    def test_category_hierarchy(self):
        """Test category hierarchy levels"""
        self.assertEqual(self.root_category.level, 0)
        self.assertEqual(self.child_category.level, 1)
        self.assertEqual(self.grandchild_category.level, 2)
    
    def test_category_full_path(self):
        """Test category full path generation"""
        expected_path = "Electronics > Smartphones > Android Phones"
        self.assertEqual(self.grandchild_category.get_full_path(), expected_path)
    
    def test_get_descendants(self):
        """Test getting descendant categories"""
        descendants = self.root_category.get_descendants()
        self.assertIn(self.child_category, descendants)
        self.assertIn(self.grandchild_category, descendants)


class ProductModelTest(TestCase):
    """Test cases for Product model"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='Smartphones',
            slug='smartphones'
        )
        self.product = Product.objects.create(
            name='iPhone 14',
            description='Latest iPhone model',
            price=Decimal('999.99'),
            sku='IPHONE14-001',
            category=self.category,
            stock_quantity=10
        )
    
    def test_product_creation(self):
        """Test product creation"""
        self.assertEqual(self.product.name, 'iPhone 14')
        self.assertEqual(self.product.price, Decimal('999.99'))
        self.assertTrue(self.product.is_in_stock)
    
    def test_product_out_of_stock(self):
        """Test product out of stock"""
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_in_stock)


class APITestCaseBase(APITestCase):
    """Base test case for API tests"""
    
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create_user(
            email='test@example.com',
            username='testuser',
            first_name='John',
            last_name='Doe',
            phone_number='+254700000000',
            password='testpassword123'
        )
        self.token = Token.objects.create(user=self.customer)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        # Create test categories and products
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='A test product',
            price=Decimal('99.99'),
            sku='TEST-001',
            category=self.category,
            stock_quantity=10
        )


class CustomerAPITest(APITestCaseBase):
    """Test cases for Customer API endpoints"""
    
    def test_customer_registration(self):
        """Test customer registration endpoint"""
        self.client.credentials()  # Remove authentication
        url = reverse('customer_order:customer-register')
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '+254700000001',
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Customer.objects.filter(email='newuser@example.com').exists())
    
    def test_customer_profile_view(self):
        """Test customer profile endpoint"""
        url = reverse('customer_order:customer-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')


class CategoryAPITest(APITestCaseBase):
    """Test cases for Category API endpoints"""
    
    def test_category_list(self):
        """Test category list endpoint"""
        url = reverse('customer_order:category-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_category_creation(self):
        """Test category creation endpoint"""
        url = reverse('customer_order:category-list-create')
        data = {
            'name': 'Books',
            'slug': 'books',
            'description': 'All kinds of books'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name='Books').exists())
    
    def test_category_average_price(self):
        """Test category average price endpoint"""
        url = reverse('customer_order:category-average-price', kwargs={'category_id': self.category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['average_price']), 99.99)


class ProductAPITest(APITestCaseBase):
    """Test cases for Product API endpoints"""
    
    def test_product_list(self):
        """Test product list endpoint"""
        url = reverse('customer_order:product-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_product_creation_with_categories(self):
        """Test product creation with category hierarchy"""
        url = reverse('customer_order:product-list-create')
        data = {
            'name': 'New Product',
            'description': 'A new test product',
            'price': '149.99',
            'sku': 'NEW-001',
            'stock_quantity': 5,
            'categories': ['Electronics', 'Computers', 'Laptops']
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if categories were created
        self.assertTrue(Category.objects.filter(name='Computers').exists())
        self.assertTrue(Category.objects.filter(name='Laptops').exists())
    
    def test_product_search(self):
        """Test product search functionality"""
        url = reverse('customer_order:product-list-create') + '?search=Test'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class OrderAPITest(APITestCaseBase):
    """Test cases for Order API endpoints"""
    
    def test_order_creation(self):
        """Test order creation endpoint"""
        url = reverse('customer_order:order-list-create')
        data = {
            'shipping_address': '123 Test Street, Nairobi',
            'notes': 'Please deliver in the morning',
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 2
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if order was created
        order = Order.objects.get(id=response.data['id'])
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.total_amount, Decimal('199.98'))  # 2 * 99.99
        
        # Check if stock was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)  # 10 - 2
    
    def test_order_list(self):
        """Test order list endpoint"""
        # Create an order first
        order = Order.objects.create(
            customer=self.customer,
            shipping_address='123 Test Street',
            total_amount=Decimal('99.99')
        )
        
        url = reverse('customer_order:order-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_insufficient_stock_order(self):
        """Test order creation with insufficient stock"""
        url = reverse('customer_order:order-list-create')
        data = {
            'shipping_address': '123 Test Street, Nairobi',
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 20  # More than available stock (10)
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient stock', str(response.data))


class OrderStatisticsAPITest(APITestCaseBase):
    """Test cases for Order Statistics API"""
    
    def test_order_statistics(self):
        """Test order statistics endpoint"""
        # Create some test orders
        Order.objects.create(
            customer=self.customer,
            shipping_address='123 Test Street',
            total_amount=Decimal('99.99'),
            status='completed'
        )
        Order.objects.create(
            customer=self.customer,
            shipping_address='456 Another Street',
            total_amount=Decimal('149.99'),
            status='pending'
        )
        
        url = reverse('customer_order:order-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_orders'], 2)
        self.assertEqual(float(response.data['total_spent']), 249.98)


class CategoryTreeAPITest(APITestCaseBase):
    """Test cases for Category Tree API"""
    
    def test_category_tree_structure(self):
        """Test category tree endpoint"""
        # Create a category hierarchy
        child_category = Category.objects.create(
            name='Smartphones',
            slug='smartphones',
            parent=self.category
        )
        grandchild_category = Category.objects.create(
            name='Android',
            slug='android',
            parent=child_category
        )
        
        url = reverse('customer_order:category-tree')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check tree structure
        tree = response.data
        self.assertEqual(len(tree), 1)  # One root category
        self.assertEqual(tree[0]['name'], 'Electronics')
        self.assertEqual(len(tree[0]['children']), 1)  # One child
        self.assertEqual(tree[0]['children'][0]['name'], 'Smartphones')
        self.assertEqual(len(tree[0]['children'][0]['children']), 1)  # One grandchild
        self.assertEqual(tree[0]['children'][0]['children'][0]['name'], 'Android')