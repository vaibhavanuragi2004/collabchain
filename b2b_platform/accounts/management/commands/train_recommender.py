# accounts/management/commands/train_recommender.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings

# We need to configure Django settings before importing our ML script
# This is a bit of a workaround to allow the standalone script to access models
def setup_django_environment():
    """
    Manually configures the Django settings to allow standalone script execution.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'b2b_platform.settings')
    import django
    django.setup()

class Command(BaseCommand):
    help = 'Trains the K-Nearest Neighbors model for product recommendations.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the recommendation model training process...'))
        
        # Setup Django environment so our script can access models
        setup_django_environment()
        
        # Now we can import our training function
        from ml_models.recommendations import train_and_save_knn_model

        try:
            # Call the main training function
            train_and_save_knn_model()
            self.stdout.write(self.style.SUCCESS('Successfully trained and saved the recommendation model.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred during model training: {e}'))