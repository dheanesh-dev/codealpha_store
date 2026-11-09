from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.shortcuts import redirect, render

from orders.models import Order

from .forms import ProfileForm, RegisterForm, StyledAuthenticationForm
from .models import get_profile


def register(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome to Lumio, {user.first_name}! Your account has been created.')
        return redirect('store:home')
    return render(request, 'accounts/register.html', {'form': form})


class SiteLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        messages.success(self.request, f'Welcome back, {user.first_name or user.username}!')
        return super().form_valid(form)


@login_required
def profile(request):
    user_orders = Order.objects.filter(user=request.user)
    stats = {
        'orders': user_orders.count(),
        'pending': user_orders.filter(status=Order.PENDING).count(),
        'spent': user_orders.exclude(status=Order.CANCELLED).aggregate(t=Sum('total'))['t'] or 0,
    }
    return render(request, 'accounts/profile.html', {
        'profile': get_profile(request.user),
        'stats': stats,
        'recent_orders': user_orders.prefetch_related('items')[:5],
    })


@login_required
def profile_edit(request):
    profile_obj = get_profile(request.user)
    initial = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'phone': profile_obj.phone,
        'city': profile_obj.city,
    }
    form = ProfileForm(request.POST or None, initial=initial, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save(profile_obj)
        messages.success(request, 'Your profile has been updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile_edit.html', {'form': form})
