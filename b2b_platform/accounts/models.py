# from django.db import models

# Create your models here.
# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.conf import settings  # <--- THIS IS THE MISSING IMPORT
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):
    # 1. Add the new role
    ROLE_CHOICES = (
        ('buyer', 'Buyer (MSME)'),
        ('seller', 'Supplier'),
        ('logistics_provider', 'Logistics Provider'),
    )
    
    # 2. Add subscription choices
    SUBSCRIPTION_CHOICES = (
        ('trial', 'Trial'),
        ('paid', 'Paid'),
    )

    # Phone number validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', 
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    # --- UPDATED & NEW FIELDS ---
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    firm_name = models.CharField(max_length=150, blank=True)
    contact_no = models.CharField(validators=[phone_regex], max_length=17, unique=True) # Unique to prevent duplicate accounts
    operating_locations = models.TextField(blank=True, help_text="Enter comma-separated locations, e.g., Mumbai, Delhi, Bangalore")
    subscription_plan = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES, default='trial')
    
    company_name = models.CharField(max_length=100, blank=True, null=True) # You can deprecate this in favor of firm_name or keep for compatibility
    # business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, blank=True, null=True) # You might want to update these choices
    city = models.CharField(max_length=50, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

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
