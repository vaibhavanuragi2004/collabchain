# from django.db import models

# Create your models here.
# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.conf import settings  # <--- THIS IS THE MISSING IMPORT
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )
    BUSINESS_TYPES = (
        ('manufacturer', 'Manufacturer'),
        ('wholesaler', 'Wholesaler'),
        ('retailer', 'Retailer'),
        ('trader', 'Trader'),
    )

    # We don't need a username, but we'll keep it for Django admin compatibility.
    # The login field will be email.
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    company_name = models.CharField(max_length=100, blank=True, null=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True)

    # Make email unique and the primary identifier
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # 'username' is still required for createsuperuser

    def __str__(self):
        return self.email


class Product(models.Model):
    # Add the category choices here
    CATEGORY_CHOICES = [
        ('steel', 'Steel Products'),
        ('cement', 'Cement & Concrete'),
        ('paints', 'Paints & Coatings'),
        ('construction', 'Construction Materials'),
        ('plumbing', 'Plumbing & Fittings'),
        ('soap', 'Soaps & Detergents'),
        ('chemicals', 'Chemicals & Solvents'),
        ('cleaning', 'Cleaning Supplies'),
        ('plastic', 'Plastic Products'),
        ('electricals', 'Electricals'),
        ('equipment', 'Industrial Equipment'),
        ('packaging', 'Packaging Materials'),
        ('tools', 'Tools & Hardware'),
        ('stationery', 'Stationery & Office Supplies'),
        ('garments', 'Textile & Garments'),
        ('food', 'Food Raw Materials'),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    # Add the new category field
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='tools')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending_approval', 'Pending Approval'), # Seller needs to approve
        ('pending_payment', 'Pending Payment'),   # Buyer needs to pay
        ('paid', 'Paid'),                         # Buyer has paid
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    
    # Corrected buyer field with a unique related_name
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders_placed'  # This is now unique and descriptive
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders_received' # Unique and descriptive
    )


    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_approval')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} for {self.product.name} by {self.buyer.email}"    


    def save(self, *args, **kwargs):
        # If the object is being created for the first time (it has no pk yet),
        # then set the seller from the related product.
        if not self.pk:
            self.seller = self.product.seller
        super().save(*args, **kwargs) # Call the "real" save() method.

class OrderStatusHistory(models.Model):
    """
    A model to log every status change for an order, creating a timeline.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history_events')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp'] # Ensure history is always in chronological order

    def __str__(self):
        return f"{self.order.id}: {self.status} at {self.timestamp}"     
           
class Message(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp'] # Ensure messages are always ordered chronologically

    def __str__(self):
        return f"Message from {self.sender} on Order #{self.order.id}"        