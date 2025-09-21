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


class RegistrationView(View):
    # This view is fine as is
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})
    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
        return render(request, 'accounts/register.html', {'form': form})


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