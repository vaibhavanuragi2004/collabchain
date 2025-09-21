# accounts/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User,Product,Message

class UserRegistrationForm(forms.ModelForm):
    """
    A form for creating new users. Includes password confirmation.
    """
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ('email', 'username', 'role', 'company_name', 'business_type', 'city')

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        # Make company_name and business_type not required by default
        self.fields['company_name'].required = False
        self.fields['business_type'].required = False
        self.fields['username'].help_text = "Required for admin access, but you will log in with your email."


    def clean_password2(self):
        # Check that the two password entries match
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean(self):
        # Custom validation for role-specific fields
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        company_name = cleaned_data.get('company_name')

        if role == 'seller' and not company_name:
            self.add_error('company_name', 'Company name is required for sellers.')

        return cleaned_data

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
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