from django.db.models import Sum

from .models import CartItem


def cart_summary(request):
    count = 0
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        count = CartItem.objects.filter(cart__user=user).aggregate(n=Sum('quantity'))['n'] or 0
    return {'cart_count': count}
