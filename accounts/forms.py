from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from config.forms import StyledFormMixin

from .models import phone_validator


class RegisterForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=30, label='First name')
    email = forms.EmailField(label='Email address')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'username', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name'].strip()
        if commit:
            user.save()
        return user


class StyledAuthenticationForm(StyledFormMixin, AuthenticationForm):
    pass


class ProfileForm(StyledFormMixin, forms.Form):
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, required=False, label='Last name')
    email = forms.EmailField(label='Email address')
    phone = forms.CharField(max_length=16, required=False, validators=[phone_validator])
    city = forms.CharField(max_length=80, required=False)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('This email is already used by another account.')
        return email

    def save(self, profile):
        data = self.cleaned_data
        self.user.first_name = data['first_name'].strip()
        self.user.last_name = data['last_name'].strip()
        self.user.email = data['email']
        self.user.save(update_fields=['first_name', 'last_name', 'email'])
        profile.phone = data['phone']
        profile.city = data['city'].strip()
        profile.save()
