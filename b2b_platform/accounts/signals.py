# accounts/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory

@receiver(post_save, sender=Order)
def log_order_status_change(sender, instance, created, **kwargs):
    """
    A signal receiver that creates a history record every time an Order's
    status is saved.
    """
    # If the order is being created for the first time
    if created:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status
        )
    else:
        # If the order is being updated, check if the status has changed
        try:
            # Get the most recent history event for this order
            last_event = instance.history_events.latest('timestamp')
            if last_event.status != instance.status:
                # If the status is different, create a new history record
                OrderStatusHistory.objects.create(
                    order=instance,
                    status=instance.status
                )
        except OrderStatusHistory.DoesNotExist:
            # Fallback in case history is empty but order is being updated
            OrderStatusHistory.objects.create(
                order=instance,
                status=instance.status
            )