# accounts/middleware.py

from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class SubscriptionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # The entire logic of this middleware should ONLY run if a user is
        # authenticated and is not a staff member.
        if request.user.is_authenticated and not request.user.is_staff:
            
            # --- START of logic for logged-in users ---

            # First, check if the user is on an active trial and calculate remaining days.
            # This data is then used by the banner in base.html.
            if request.user.subscription_plan == 'trial' and hasattr(request.user, 'subscription_end_date') and request.user.subscription_end_date:
                now = timezone.now()
                remaining_time = request.user.subscription_end_date - now
                if remaining_time.days >= 0:
                    request.trial_days_remaining = remaining_time.days

            # Second, check if the user's trial has expired and block them if needed.
            # This is the "gatekeeper" logic.
            
            # List of pages an expired user is ALWAYS allowed to see.
            allowed_urls = [
                reverse('subscribe'), 
                reverse('logout'),
                reverse('payment_verify')
            ]

            # If the user is trying to access a page that is allowed, let them pass.
            if request.path in allowed_urls:
                return self.get_response(request)

            # If the user is on a paid plan, let them pass.
            if request.user.subscription_plan == 'paid':
                return self.get_response(request)
                
            # Finally, check if the trial has expired.
            if hasattr(request.user, 'subscription_end_date') and request.user.subscription_end_date:
                if request.user.subscription_end_date < timezone.now():
                    messages.info(request, "Your trial has expired. Please subscribe to continue.")
                    return redirect('subscribe')

            # --- END of logic for logged-in users ---

        # If the user is NOT authenticated or IS a staff member,
        # do nothing and just process the request as normal.
        return self.get_response(request)