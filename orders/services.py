from django.db import transaction
from django.db.models import F

from cart.models import Cart
from store.models import Product

from .models import Order, OrderItem, ShippingAddress


class CheckoutError(Exception):
    def __init__(self, messages):
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__('; '.join(self.messages))


@transaction.atomic
def place_order(user, address_data):
    """Turn the user's cart into an order.

    Everything happens in one transaction: the products are locked, stock is
    re-checked, the order is created, stock is reduced and the cart is emptied.
    If anything fails nothing is saved.
    """
    cart = Cart.objects.select_for_update().filter(user=user).first()
    items = list(cart.items.select_related('product')) if cart else []
    if not items:
        raise CheckoutError('Your cart is empty.')

    products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[i.product_id for i in items])}

    problems = []
    for item in items:
        product = products.get(item.product_id)
        if product is None or not product.is_active:
            problems.append(f'"{item.product.name}" is no longer available. Please remove it from your cart.')
        elif product.stock == 0:
            problems.append(f'"{product.name}" is out of stock. Please remove it from your cart.')
        elif item.quantity > product.stock:
            problems.append(f'Only {product.stock} of "{product.name}" left in stock. Please reduce the quantity.')
    if problems:
        raise CheckoutError(problems)

    address = ShippingAddress.objects.create(user=user, **address_data)
    total = sum(products[i.product_id].price * i.quantity for i in items)
    order = Order.objects.create(user=user, shipping_address=address, total=total)

    OrderItem.objects.bulk_create([
        OrderItem(order=order, product=products[i.product_id], product_name=products[i.product_id].name,
                  unit_price=products[i.product_id].price, quantity=i.quantity)
        for i in items
    ])
    for item in items:
        Product.objects.filter(pk=item.product_id).update(stock=F('stock') - item.quantity)

    cart.items.all().delete()
    return order
