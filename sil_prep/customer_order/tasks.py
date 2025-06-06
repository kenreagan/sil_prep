# tasks.py
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import africastalking

# Initialize Africa's Talking SMS
africastalking.initialize(
    username=settings.AFRICAS_TALKING_USERNAME,
    api_key=settings.AFRICAS_TALKING_API_KEY
)
sms = africastalking.SMS

def send_order_sms(order_id):
    """Send SMS notification to customer about their order"""
    order = Order.objects.get(id=order_id)
    message = (
        f"Hello {order.customer.username}, your order #{order.id} "
        f"has been received. Total: Ksh. {order.total_amount}. "
        "Thank you for shopping with us!"
    )
    
    try:
        response = sms.send(message, [order.customer.phone_number])
        return response
    except Exception as e:
        # Log error
        print(f"Failed to send SMS: {e}")

def send_order_email(order_id):
    """Send email notification to admin about new order"""
    order = Order.objects.get(id=order_id)
    subject = f"New Order #{order.id} Received"
    message = (
        f"Order Details:\n\n"
        f"Customer: {order.customer.username}\n"
        f"Order ID: {order.id}\n"
        f"Status: {order.get_status_display()}\n"
        f"Total Amount: Ksh. {order.total_amount}\n\n"
        f"Items:\n"
    )
    
    for item in order.items.all():
        message += f"- {item.product.name} ({item.quantity} x Ksh. {item.price_at_purchase})\n"
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        fail_silently=False,
    )