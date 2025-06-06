from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db import transaction
from decimal import Decimal
from .models import Customer, Category, Product, Order, OrderItem


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for customer registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = [
            'email', 'username', 'first_name', 'last_name', 
            'phone_number', 'address', 'date_of_birth', 
            'password', 'password_confirm'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        customer = Customer.objects.create_user(password=password, **validated_data)
        return customer


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for customer details"""
    class Meta:
        model = Customer
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone_number', 'address', 'date_of_birth', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for categories"""
    level = serializers.ReadOnlyField()
    full_path = serializers.ReadOnlyField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'parent', 'slug', 
            'is_active', 'level', 'full_path', 'children', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_children(self, obj):
        if hasattr(obj, 'children'):
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_path = serializers.CharField(source='category.get_full_path', read_only=True)
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'sku', 'category',
            'category_name', 'category_path', 'stock_quantity', 
            'is_active', 'is_in_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating products with categories"""
    categories = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        help_text="List of category names in hierarchical order (e.g., ['Electronics', 'Computers', 'Laptops'])"
    )

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'sku', 
            'stock_quantity', 'is_active', 'categories'
        ]

    def create(self, validated_data):
        categories_data = validated_data.pop('categories')
        
        # Create or get category hierarchy
        parent_category = None
        for category_name in categories_data:
            category, created = Category.objects.get_or_create(
                name=category_name,
                parent=parent_category,
                defaults={'slug': category_name.lower().replace(' ', '-')}
            )
            parent_category = category
        
        # Assign the last (deepest) category to the product
        validated_data['category'] = parent_category
        return Product.objects.create(**validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'total_price'
        ]
        read_only_fields = ['id', 'unit_price', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    items = OrderItemSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_email', 
            'customer_name', 'status', 'total_amount', 
            'shipping_address', 'notes', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'total_amount', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}".strip()


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        help_text="List of items with product_id and quantity"
    )

    class Meta:
        model = Order
        fields = ['shipping_address', 'notes', 'items']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        
        for item in value:
            if 'product_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Each item must have product_id and quantity")
            
            try:
                product = Product.objects.get(id=item['product_id'], is_active=True)
                if item['quantity'] > product.stock_quantity:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {product.name}. Available: {product.stock_quantity}"
                    )
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Product with id {item['product_id']} not found")
        
        return value

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        customer = self.context['request'].user
        
        # Create order
        order = Order.objects.create(
            customer=customer,
            total_amount=Decimal('0.00'),
            **validated_data
        )
        
        total_amount = Decimal('0.00')
        
        # Create order items
        for item_data in items_data:
            product = Product.objects.get(id=item_data['product_id'])
            quantity = item_data['quantity']
            
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            )
            
            total_amount += order_item.total_price
            
            # Update stock
            product.stock_quantity -= quantity
            product.save()
        
        # Update total amount
        order.total_amount = total_amount
        order.save()
        
        return order


class CategoryAverageSerializer(serializers.Serializer):
    """Serializer for category average price"""
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    average_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    product_count = serializers.IntegerField()