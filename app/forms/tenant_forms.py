from django import forms
from django.contrib.auth import authenticate
from django.utils.text import slugify
from app.models import TenantProfile, User

class RegistrationForm(forms.Form):
    business_name = forms.CharField(max_length=255, label="Business Name", widget=forms.TextInput(attrs={
        'placeholder': 'e.g. Apex Pharma & Retail',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }))
    full_name = forms.CharField(max_length=255, label="Full Name", widget=forms.TextInput(attrs={
        'placeholder': 'e.g. Jane Doe',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }))
    email = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={
        'placeholder': 'admin@example.com',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': '••••••••',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }), label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': '••••••••',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }), label="Confirm Password")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        # Generate and validate slug
        business_name = cleaned_data.get('business_name')
        if business_name:
            slug = slugify(business_name)
            if TenantProfile.objects.filter(slug=slug).exists():
                self.add_error('business_name', "A business with this name/slug already exists.")
            cleaned_data['slug'] = slug

        return cleaned_data

class LoginForm(forms.Form):
    email = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={
        'placeholder': 'admin@example.com',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={
        'placeholder': '••••••••',
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-all text-sm'
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise forms.ValidationError("Invalid email or password.")
            cleaned_data['user'] = user

        return cleaned_data
