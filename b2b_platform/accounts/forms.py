# accounts/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User,Product,Message


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        # Add the new fields to the form
        fields = ('firm_name', 'email', 'contact_no', 'role', 'operating_locations', 'username', 'password', 'password2')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            # Add a placeholder to operating_locations
            'operating_locations': forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g., Mumbai, Delhi, Bangalore'}),
        }

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        # We can style all fields automatically here
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.Select):
                 field.widget.attrs.update({'class': 'form-control'})

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # Create the user as inactive until they verify their OTP
        user.is_active = False
        if commit:
            user.save()
        return user

class UserLoginForm(AuthenticationForm):
    """
    A custom login form that uses email instead of username.
    """
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    username = forms.EmailField(label="Email", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder': 'email@example.com'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Password'}))

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category','description', 'price', 'stock_quantity', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }    
# accounts/forms.py



class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...'
            })
        }
        labels = {
            'body': '' # Hide the label for a cleaner look
        }        