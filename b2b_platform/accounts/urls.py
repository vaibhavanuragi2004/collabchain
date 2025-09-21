# accounts/urls.py

from django.urls import path
from .views import (
    RegistrationView, LoginView, LogoutView,
    BuyerDashboardView, SellerDashboardView,
    ProductListView, ProductCreateView, ProductUpdateView, ProductDeleteView,
    MyOrdersView,PlaceOrderView,
    ManageOrdersView, AcceptOrderView, RejectOrderView,ProcessPaymentView,MarkAsShippedView, MarkAsCompletedView,
    OrderConversationView,
)

urlpatterns = [
    # Auth
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Dashboards
    path('dashboard/buyer/', BuyerDashboardView.as_view(), name='buyer_dashboard'),
    path('dashboard/seller/', SellerDashboardView.as_view(), name='seller_dashboard'),


    # Product CRUD
    path('dashboard/seller/products/', ProductListView.as_view(), name='product_list'),
    path('dashboard/seller/products/add/', ProductCreateView.as_view(), name='product_add'),
    path('dashboard/seller/products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_edit'),
    path('dashboard/seller/products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product_delete'),

    path('dashboard/seller/orders/', ManageOrdersView.as_view(), name='manage_orders'),
    path('dashboard/seller/orders/<int:order_id>/accept/', AcceptOrderView.as_view(), name='accept_order'),
    path('dashboard/seller/orders/<int:order_id>/reject/', RejectOrderView.as_view(), name='reject_order'),

    

    path('buyer/', BuyerDashboardView.as_view(), name='buyer_dashboard'),
    path('my-orders/', MyOrdersView.as_view(), name='my_orders'),
    path('order/place/', PlaceOrderView.as_view(), name='place_order'),
     path('payment/process/<int:order_id>/', ProcessPaymentView.as_view(), name='process_payment'),

     path('dashboard/seller/orders/<int:order_id>/ship/', MarkAsShippedView.as_view(), name='ship_order'),
    path('dashboard/seller/orders/<int:order_id>/complete/', MarkAsCompletedView.as_view(), name='complete_order'),

    path('orders/<int:order_id>/conversation/', OrderConversationView.as_view(), name='order_conversation'),

]