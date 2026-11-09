from django import forms

from config.forms import StyledFormMixin

from .models import ShippingAddress


class CheckoutForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['full_name', 'phone', 'address_line1', 'address_line2', 'city', 'state', 'pincode']
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '9876543210', 'inputmode': 'tel'}),
            'pincode': forms.TextInput(attrs={'placeholder': '600001', 'inputmode': 'numeric', 'maxlength': 6}),
        }

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()
