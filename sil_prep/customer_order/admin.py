from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Customer, Category, Product, Order, OrderItem


@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    """Admin configuration for Customer model"""
    list_display = ['email', 'first_name', 'last_name', 'phone_number', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined', 'last_login']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']
    
    # Customize the fieldsets for the Customer model
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'address', 'date_of_birth')
        }),
    )
    
    # Add fields for creating new customers
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'address', 'date_of_birth')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model"""
    list_display = ['name', 'parent', 'level_display', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']
    
    def level_display(self, obj):
        """Display category level with indentation"""
        return format_html(
            '<span style="margin-left: {}px;">{}</span>',
            obj.level * 20,
            '└─ ' * obj.level + obj.name
        )
    level_display.short_description = 'Hierarchy'
    
    def product_count(self, obj):
        """Display number of products in this category"""
        count = obj.products.filter(is_active=True).count()
        if count > 0:
            url = reverse('admin:store_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} products</a>', url, count)
        return '0 products'
    product_count.short_description = 'Products'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for Product model"""
    list_display = ['name', 'sku', 'category', 'price', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['name', 'sku', 'description']
    list_editable = ['price', 'stock_quantity', 'is_active']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'sku', 'category')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'stock_quantity', 'is_active')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


class OrderItemInline(admin.TabularInline):
    """Inline admin for OrderItem"""
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']
    fields = ['product', 'quantity', 'unit_price', 'total_price']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model"""
    list_display = ['order_number', 'customer_name', 'customer_email', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer__email', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['order_number', 'total_amount', 'created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'status', 'total_amount')
        }),
        ('Shipping & Notes', {
            'fields': ('shipping_address', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def customer_name(self, obj):
        """Display customer full name"""
        return f"{obj.customer.first_name} {obj.customer.last_name}".strip()
    customer_name.short_description = 'Customer'
    
    def customer_email(self, obj):
        """Display customer email"""
        return obj.customer.email
    customer_email.short_description = 'Email'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin configuration for OrderItem model"""
    list_display = ['order', 'product', 'quantity', 'unit_price', 'total_price', 'created_at']
    list_filter = ['created_at', 'product__category']
    search_fields = ['order__order_number', 'product__name', 'product__sku']
    readonly_fields = ['total_price']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'product')


# Customize admin site headers
admin.site.site_header = 'Store Administration'
admin.site.site_title = 'Store Admin'
admin.site.index_title = 'Welcome to Store Administration'