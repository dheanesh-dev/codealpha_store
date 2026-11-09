from django.conf import settings
from django.db import models
from django.db.models import Q

from store.models import Product


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart of {self.user.username}'

    def get_items(self):
        return list(self.items.select_related('product', 'product__category').order_by('id'))

    @staticmethod
    def total_of(items):
        return sum((item.line_total for item in items), 0)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_product_per_cart'),
            models.CheckConstraint(condition=Q(quantity__gte=1), name='cartitem_quantity_gte_1'),
        ]

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    @property
    def line_total(self):
        return self.product.price * self.quantity


def get_cart(user):
    return Cart.objects.get_or_create(user=user)[0]
