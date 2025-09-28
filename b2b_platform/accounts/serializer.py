# accounts/serializers.py

from rest_framework import serializers
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm Password')

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password2', 'role', 'company_name', 'business_type', 'city')
        extra_kwargs = {
            'company_name': {'required': False},
            'business_type': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Additional validation based on role
        if attrs.get('role') == 'seller' and not attrs.get('company_name'):
             raise serializers.ValidationError({"company_name": "Company name is required for sellers."})

        return attrs

    def create(self, validated_data):
        # We pop the password2 field as it's not part of the User model
        validated_data.pop('password2')
        # We pop the password and use set_password to hash it
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user