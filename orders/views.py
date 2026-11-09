from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import get_profile
from cart.models import Cart, get_cart

from .forms import CheckoutForm
from .models import Order, ShippingAddress
from .services import CheckoutError, place_order


def _initial_address(user):
    last = ShippingAddress.objects.filter(user=user).first()
    if last:
        return {f: getattr(last, f) for f in CheckoutForm.Meta.fields}
    profile = get_profile(user)
    return {'full_name': user.get_full_name(), 'phone': profile.phone, 'city': profile.city}


@login_required
def checkout(request):
    cart = get_cart(request.user)
    items = cart.get_items()
    if not items:
        messages.info(request, 'Your cart is empty. Add some products before checking out.')
        return redirect('cart:detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request.user, form.cleaned_data)
            except CheckoutError as error:
                for message in error.messages:
                    messages.error(request, message)
                return redirect('cart:detail')
            messages.success(request, f'Thank you! Your order {order.order_id} has been placed.')
            return redirect('orders:confirmation', order_id=order.order_id)
        messages.error(request, 'Please correct the errors in the delivery details.')
    else:
        form = CheckoutForm(initial=_initial_address(request.user))

    return render(request, 'orders/checkout.html', {
        'form': form, 'items': items, 'subtotal': Cart.total_of(items)})


def _own_order(request, order_id):
    queryset = Order.objects.select_related('shipping_address').prefetch_related('items')
    return get_object_or_404(queryset, order_id=order_id, user=request.user)


@login_required
def confirmation(request, order_id):
    return render(request, 'orders/detail.html', {'order': _own_order(request, order_id), 'just_placed': True})


@login_required
def order_detail(request, order_id):
    return render(request, 'orders/detail.html', {'order': _own_order(request, order_id), 'just_placed': False})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/history.html', {'page': Paginator(orders, 8).get_page(request.GET.get('page'))})


@login_required
@require_POST
def cancel_order(request, order_id):
    order = _own_order(request, order_id)
    try:
        order.set_status(Order.CANCELLED)
        messages.success(request, f'Order {order.order_id} has been cancelled.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('orders:detail', order_id=order.order_id)
