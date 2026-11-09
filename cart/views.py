from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.views.decorators.http import require_POST

from store.models import Product

from .models import Cart, CartItem, get_cart

MAX_QUANTITY = 99


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _safe_next(request, fallback):
    target = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return fallback


def _count(user):
    return CartItem.objects.filter(cart__user=user).aggregate(n=Sum('quantity'))['n'] or 0


def _respond(request, ok, message, fallback):
    if _is_ajax(request):
        return JsonResponse({'ok': ok, 'message': message, 'count': _count(request.user)},
                            status=200 if ok else 400)
    (messages.success if ok else messages.error)(request, message)
    return redirect(_safe_next(request, fallback))


def _parse_quantity(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@login_required
def cart_detail(request):
    cart = get_cart(request.user)
    items = cart.get_items()
    return render(request, 'cart/cart.html', {
        'items': items,
        'subtotal': Cart.total_of(items),
        'has_problem': any(i.quantity > i.product.stock or not i.product.is_active for i in items),
    })


@require_POST
def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        target = urlparse(_safe_next(request, '/'))._replace(scheme='', netloc='').geturl() or '/'
        login_url = f"{reverse('accounts:login')}?{urlencode({'next': target})}"
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'login_url': login_url,
                                 'message': 'Please log in to add items to your cart.'}, status=401)
        messages.info(request, 'Please log in to add items to your cart.')
        return redirect(login_url)

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    quantity = _parse_quantity(request.POST.get('quantity'))
    fallback = product.get_absolute_url()

    if quantity is None or quantity < 1 or quantity > MAX_QUANTITY:
        return _respond(request, False, f'Please choose a quantity between 1 and {MAX_QUANTITY}.', fallback)

    with transaction.atomic():
        cart = get_cart(request.user)
        item = CartItem.objects.select_for_update().filter(cart=cart, product=product).first()
        current = item.quantity if item else 0
        if not product.in_stock:
            return _respond(request, False, f'Sorry, "{product.name}" is out of stock.', fallback)
        if current + quantity > product.stock:
            left = product.stock - current
            msg = (f'Only {product.stock} of "{product.name}" available, and you already have {current} in your cart.'
                   if current else f'Only {product.stock} of "{product.name}" available.')
            if left <= 0:
                msg = f'You already have all {product.stock} available units of "{product.name}" in your cart.'
            return _respond(request, False, msg, fallback)
        if current + quantity > MAX_QUANTITY:
            return _respond(request, False, f'You can order at most {MAX_QUANTITY} units of one product.', fallback)
        if item:
            item.quantity = current + quantity
            item.save(update_fields=['quantity'])
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=quantity)

    return _respond(request, True, f'"{product.name}" added to your cart.', fallback)


@login_required
@require_POST
def update_item(request, item_id):
    item = get_object_or_404(CartItem.objects.select_related('product'), pk=item_id, cart__user=request.user)
    action = request.POST.get('action')
    if action == 'inc':
        new_qty = item.quantity + 1
    elif action == 'dec':
        new_qty = item.quantity - 1
    elif action == 'set':
        new_qty = _parse_quantity(request.POST.get('quantity'))
        if new_qty is None:
            messages.error(request, 'Please enter a valid quantity.')
            return redirect('cart:detail')
    else:
        messages.error(request, 'Invalid cart action.')
        return redirect('cart:detail')

    product = item.product
    if new_qty < 1:
        item.delete()
        messages.success(request, f'"{product.name}" removed from your cart.')
    elif new_qty > MAX_QUANTITY:
        messages.error(request, f'You can order at most {MAX_QUANTITY} units of one product.')
    elif new_qty > product.stock:
        messages.error(request, f'Only {product.stock} of "{product.name}" available.')
    else:
        item.quantity = new_qty
        item.save(update_fields=['quantity'])
        messages.success(request, f'Quantity of "{product.name}" updated to {new_qty}.')
    return redirect('cart:detail')


@login_required
@require_POST
def remove_item(request, item_id):
    item = get_object_or_404(CartItem.objects.select_related('product'), pk=item_id, cart__user=request.user)
    name = item.product.name
    item.delete()
    messages.success(request, f'"{name}" removed from your cart.')
    return redirect('cart:detail')
