from decimal import Decimal

from django import forms

from config.forms import StyledFormMixin
from store.models import Category, Product

MAX_IMAGE_MB = 3


class ProductForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'stock', 'image', 'is_active', 'is_featured']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
        }

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < Decimal('0.01'):
            raise forms.ValidationError('Price must be at least 0.01.')
        return price

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'size') and image.size > MAX_IMAGE_MB * 1024 * 1024:
            raise forms.ValidationError(f'Image is too large (maximum {MAX_IMAGE_MB} MB).')
        return image


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon']

    def clean_name(self):
        return self.cleaned_data['name'].strip()


class OrderStatusForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=[])

    def __init__(self, *args, order, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = order.next_statuses
