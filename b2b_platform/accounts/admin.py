# from django.contrib import admin

# Register your models here.
# accounts/admin.py
from django.contrib import admin
from .models import User

admin.site.register(User)