# accounts/views.py

# Django's standard function and class-based view imports
from django.shortcuts import render, redirect,get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

# Django's authentication imports for functions and mixins
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages  # Import the messages framework
# Your local app's models and forms
# accounts/views.py

from .models import Product, Order, User, Message # Add Message
from .forms import UserRegistrationForm, UserLoginForm, ProductForm, MessageForm # Add MessageForm
from twilio.rest import Client
from django.conf import settings
from datetime import timedelta      # Make sure this is at the top of the file
from django.utils import timezone   # Make sure this is also at the top
import random
import razorpay

class RegistrationView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Generate 6-digit OTP
            otp = random.randint(100000, 999999)
            
            # Store OTP and user's phone number in session for verification
            request.session['otp'] = otp
            request.session['user_id'] = user.id
            request.session['contact_no'] = user.contact_no

            # --- Send OTP via Twilio ---
            try:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=f"Your B2B-Nexus verification code is: {otp}",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=user.contact_no
                )
                print(f"OTP Sent to {user.contact_no}, SID: {message.sid}") # For debugging
                messages.success(request, f"An OTP has been sent to {user.contact_no}.")
            except Exception as e:
                messages.error(request, f"Failed to send OTP. Please check the phone number. Error: {e}")
                user.delete() # Delete the inactive user if SMS fails
                return render(request, 'accounts/register.html', {'form': form})

            return redirect('verify_otp')
        
        return render(request, 'accounts/register.html', {'form': form})

class VerifyOTPView(View):
    def get(self, request):
        # Check if the session data exists
        if 'contact_no' not in request.session:
            messages.error(request, "Session expired. Please register again.")
            return redirect('register')
        
        contact_no = request.session.get('contact_no')
        return render(request, 'accounts/verify_otp.html', {'contact_no': contact_no})

    def post(self, request):
        submitted_otp = request.POST.get('otp')
        session_otp = request.session.get('otp')
        user_id = request.session.get('user_id')

        if not all([submitted_otp, session_otp, user_id]):
            messages.error(request, "Your session has expired. Please try registering again.")
            return redirect('register')

        if int(submitted_otp) == session_otp:
            try:
                user = User.objects.get(id=user_id)
                user.is_active = True
                user.save()
                
                # Clean up session
                del request.session['otp']
                del request.session['user_id']
                del request.session['contact_no']
                
                login(request, user)
                messages.success(request, "Your account has been successfully verified!")
                
                # Redirect based on role
                if user.role == 'buyer':
                    return redirect('buyer_dashboard')
                else: # Seller or Logistics Provider
                    return redirect('seller_dashboard') # Or a generic dashboard

            except User.DoesNotExist:
                messages.error(request, "User not found. Please register again.")
                return redirect('register')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')


class LoginView(View):
    def get(self, request):
        form = UserLoginForm()
        return render(request, 'accounts/login.html', {'form': form})
    def post(self, request):
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Use Django's login function to create a session
            login(request, user)
            
            if user.role == 'buyer':
                return redirect('buyer_dashboard')
            else:
                return redirect('seller_dashboard')
        else:
            return render(request, 'accounts/login.html', {'form': form})


class LogoutView(View):
    def get(self, request):
        # Use Django's logout function to destroy the session
        logout(request)
        return redirect('login')

class SubscriptionView(LoginRequiredMixin, View):
    def get(self, request):
        # Create a Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create a Razorpay Order
        payment_amount = 100000 # Amount in paise (1000 INR)
        payment_currency = 'INR'
        payment_data = {
            'amount': payment_amount,
            'currency': payment_currency,
        }
        razorpay_order = client.order.create(data=payment_data)
        
        context = {
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': payment_amount,
            'firm_name': request.user.firm_name,
            'contact_no': request.user.contact_no,
            'email': request.user.email,
        }
        return render(request, 'accounts/subscribe.html', context)

class PaymentVerificationView(View):
    def post(self, request):
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            # Get the payment data from the POST request
            razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            razorpay_signature = request.POST.get('razorpay_signature', '')
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify the signature
            client.utility.verify_payment_signature(params_dict)

            # If verification is successful, update the user's subscription
            user = request.user
            user.subscription_plan = 'paid'
            user.subscription_end_date = timezone.now() + timedelta(days=365) # 1 year subscription
            user.save()
            
            messages.success(request, "Subscription successful! You now have full access.")
            return redirect('buyer_dashboard' if user.role == 'buyer' else 'seller_dashboard')

        except Exception as e:
            messages.error(request, f"Payment failed. Please try again. Error: {e}")
            return redirect('subscribe')

# --- DASHBOARD VIEWS (Refactored for Sessions) ---

class BuyerDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.role != 'buyer':
            return redirect('login')
        return render(request, 'buyer_dashboard.html')


class SellerDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.role != 'seller':
            return redirect('login')
        return render(request, 'seller_dashboard.html')


# --- SECURITY MIXIN for Product Views ---
class SellerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'seller'
    
    def handle_no_permission(self):
        # For better UX, you might want to redirect to the seller dashboard 
        # or show a 'permission denied' page, but login is a safe default.
        return redirect('login')



# --- PRODUCT CRUD VIEWS (Now inside accounts app) ---

class ProductListView(SellerRequiredMixin, ListView):
    model = Product
    template_name = 'accounts/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        # Ensure that sellers only see their own products
        return Product.objects.filter(seller=self.request.user).order_by('-created_at')

class ProductCreateView(SellerRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'accounts/product_form.html'
    success_url = reverse_lazy('product_list')
    
    def form_valid(self, form):
        # Automatically assign the logged-in seller to the product
        form.instance.seller = self.request.user
        return super().form_valid(form)

class ProductUpdateView(SellerRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'accounts/product_form.html'
    success_url = reverse_lazy('product_list')
    
    def get_queryset(self):
        # Crucial security check: ensure a seller can't edit another seller's products
        return Product.objects.filter(seller=self.request.user)

class ProductDeleteView(SellerRequiredMixin, DeleteView):
    model = Product
    template_name = 'accounts/product_confirm_delete.html'
    success_url = reverse_lazy('product_list')
    
    def get_queryset(self):
        # Crucial security check: ensure a seller can't delete another seller's products
        return Product.objects.filter(seller=self.request.user)



class BuyerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self): return self.request.user.role == 'buyer'
    def handle_no_permission(self): return redirect('login')

# --- BUYER VIEWS ---

class BuyerDashboardView(BuyerRequiredMixin, ListView):
    model = Product
    template_name = 'accounts/all_products.html'
    context_object_name = 'products'
    paginate_by = 12  # Optional: to keep the page clean

    def get_queryset(self):
        queryset = Product.objects.all().order_by('-created_at')
        # Search functionality
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        # Category filter functionality
        category_filter = self.request.GET.get('category', '')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Product.CATEGORY_CHOICES
        # Pass search and filter values back to template to keep them in the form
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context

class PlaceOrderView(BuyerRequiredMixin, View):
    def post(self, request):
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        
        product = get_object_or_404(Product, id=product_id)
        
        if not quantity or int(quantity) <= 0:
            messages.error(request, 'Please enter a valid quantity.')
            return redirect('buyer_dashboard')

        if int(quantity) > product.stock_quantity:
            messages.error(request, f'Only {product.stock_quantity} items are in stock.')
            return redirect('buyer_dashboard')

        # Create the order
        Order.objects.create(
            product=product,
            buyer=request.user,
            quantity=int(quantity)
        )
        
        messages.success(request, f'Order request for {product.name} has been sent!')
        # return redirect('buyer_dashboard')
        return redirect('my_orders') # Redirect to My Orders page to see the new order

# Static view for "My Orders" for now
# class MyOrdersView(BuyerRequiredMixin, View):
#     def get(self, request):
#         # Later, this will show a list of orders. For now, it's a static page.
#         return render(request, 'accounts/my_orders.html')

class MyOrdersView(BuyerRequiredMixin, ListView): # Changed from View to ListView
    model = Order
    template_name = 'accounts/my_orders.html'
    context_object_name = 'orders'
    def get_queryset(self):
        # This now fetches orders from the database for the logged-in buyer
        return Order.objects.filter(buyer=self.request.user).order_by('-created_at')        

class ManageOrdersView(SellerRequiredMixin, ListView):
    model = Order
    template_name = 'accounts/manage_orders.html'
    context_object_name = 'orders'
    def get_queryset(self): return Order.objects.filter(seller=self.request.user).order_by('-created_at')

class AcceptOrderView(SellerRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, seller=request.user)
        order.status = 'pending_payment'
        order.save()
        messages.success(request, f'Order #{order.id} has been accepted. Waiting for buyer payment.')
        return redirect('manage_orders')

class RejectOrderView(SellerRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, seller=request.user)
        order.status = 'rejected'
        order.save()
        messages.info(request, f'Order #{order.id} has been rejected.')
        return redirect('manage_orders')
class MarkAsShippedView(SellerRequiredMixin, View):
    def post(self, request, order_id):
        # Security check: ensure the order exists, belongs to this seller, and is in the correct status
        order = get_object_or_404(Order, id=order_id, seller=request.user, status='paid')
        
        # Update the status
        order.status = 'shipped'
        order.save()
        
        messages.success(request, f"Order #{order.id} has been marked as shipped.")
        return redirect('manage_orders')

class MarkAsCompletedView(SellerRequiredMixin, View):
    def post(self, request, order_id):
        # Security check: ensure order belongs to seller and is in 'shipped' status
        order = get_object_or_404(Order, id=order_id, seller=request.user, status='shipped')
        
        # Update the status
        order.status = 'completed'
        order.save()
        
        messages.success(request, f"Order #{order.id} has been marked as completed.")
        return redirect('manage_orders')        


# New view for handling the mock payment
class ProcessPaymentView(BuyerRequiredMixin, View):
    def get(self, request, order_id):
        # Fetch the order that needs to be paid for
        order = get_object_or_404(Order, id=order_id, buyer=request.user, status='pending_payment')
        context = {
            'order': order,
            'total_price': order.quantity * order.product.price
        }
        return render(request, 'accounts/process_payment.html', context)

    def post(self, request, order_id):
        # This is where the "payment" is processed
        order = get_object_or_404(Order, id=order_id, buyer=request.user)
        product = order.product

        # 1. Update the order status
        order.status = 'paid'
        order.save()

        # 2. Decrease the product's stock
        product.stock_quantity -= order.quantity
        product.save()

        # 3. Add a success message
        messages.success(request, f"Payment for Order #{order.id} was successful!")

        # 4. Redirect back to the order list
        return redirect('my_orders')

# accounts/views.py

import razorpay # Add this import at the top
from datetime import timedelta # Ensure timedelta is imported

# ... (all your existing views are above this) ...

# === SUBSCRIPTION & PAYMENT VIEWS ===

class SubscriptionView(LoginRequiredMixin, View):
    """
    Handles displaying the subscription page and creating a Razorpay order.
    """
    def get(self, request):
        # Create a Razorpay client instance
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Define payment details
        payment_amount = 100000  # Amount in paise (e.g., 1000 INR)
        payment_currency = 'INR'
        
        # Create the Order on Razorpay's servers
        payment_data = {
            'amount': payment_amount,
            'currency': payment_currency,
        }
        razorpay_order = client.order.create(data=payment_data)

        # Pass the necessary data to the template
        context = {
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': payment_amount,
            'firm_name': request.user.firm_name,
            'contact_no': request.user.contact_no,
            'email': request.user.email,
        }
        return render(request, 'accounts/subscribe.html', context)


class PaymentVerificationView(LoginRequiredMixin, View):
    """
    Handles the verification of the payment after the user completes it on Razorpay.
    This view must be accessible to expired users, which we configured in the middleware.
    """
    def post(self, request):
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        try:
            # Get the payment data from the form submitted by Razorpay's JS
            razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            razorpay_signature = request.POST.get('razorpay_signature', '')
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify the payment signature. This is a crucial security step.
            # Throws an exception if the signature is invalid.
            client.utility.verify_payment_signature(params_dict)

            # If verification is successful, update the user's subscription
            user = request.user
            user.subscription_plan = 'paid'
            user.subscription_end_date = timezone.now() + timedelta(days=365)  # Grant a 1-year subscription
            user.save()
            
            messages.success(request, "Subscription successful! You now have full access.")
            
            # Redirect to the appropriate dashboard
            if user.role == 'buyer':
                return redirect('buyer_dashboard')
            else: # Seller or Logistics Provider
                return redirect('seller_dashboard')

        except Exception as e:
            messages.error(request, f"Payment verification failed. Please try again or contact support.")
            return redirect('subscribe')

# ... (Place this at the end of the file)

from django.db.models import Q # Add this import for complex queries

class OrderConversationView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        # Security check: ensure the user is either the buyer or seller for this order
        order = get_object_or_404(Order.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ), id=order_id)
        
        messages = order.messages.all()
        form = MessageForm()
        
        context = {
            'order': order,
            'messages': messages,
            'form': form,
        }
        return render(request, 'accounts/order_conversation.html', context)

    def post(self, request, order_id):
        # Same security check as the GET method
        order = get_object_or_404(Order.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ), id=order_id)

        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.order = order
            message.sender = request.user
            message.save()
            return redirect('order_conversation', order_id=order.id)
        
        # If form is invalid, re-render the page with the errors
        messages_list = order.messages.all()
        context = {
            'order': order,
            'messages': messages_list,
            'form': form,
        }
        return render(request, 'accounts/order_conversation.html', context)        

# accounts/views.py

# Add this to your imports at the top of the file
from ml_models.recommendations import get_recommendations

# ... (other views remain the same)

class BuyerDashboardView(BuyerRequiredMixin, ListView):
    model = Product
    template_name = 'accounts/all_products.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        # This logic remains unchanged
        queryset = Product.objects.all().order_by('-created_at')
        search_query = self.request.GET.get('q', '')
        if search_query: queryset = queryset.filter(name__icontains=search_query)
        category_filter = self.request.GET.get('category', '')
        if category_filter: queryset = queryset.filter(category=category_filter)
        return queryset

    def get_context_data(self, **kwargs):
        # This is where we add the recommendation logic
        context = super().get_context_data(**kwargs)
        context['categories'] = Product.CATEGORY_CHOICES
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_category'] = self.request.GET.get('category', '')

        # --- ADD THIS BLOCK ---
        if self.request.user.is_authenticated:
            recommended_products = get_recommendations(self.request.user, num_recs=4)
            context['recommended_products'] = recommended_products
        # --- END BLOCK ---

        return context