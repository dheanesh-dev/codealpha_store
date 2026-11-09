from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from orders.models import Order
from store.models import LOW_STOCK_THRESHOLD, Category, Product

from .decorators import staff_required
from .forms import CategoryForm, OrderStatusForm, ProductForm

MAX_STOCK = 100000


# ---------- overview ----------
@staff_required
def overview(request):
    valid_orders = Order.objects.exclude(status=Order.CANCELLED)
    status_counts = {code: 0 for code, _ in Order.STATUS_CHOICES}
    for row in Order.objects.values('status').annotate(n=Count('id')):
        status_counts[row['status']] = row['n']
    context = {
        'product_count': Product.objects.count(),
        'category_count': Category.objects.count(),
        'customer_count': User.objects.filter(is_staff=False).count(),
        'order_count': Order.objects.count(),
        'revenue': valid_orders.aggregate(t=Sum('total'))['t'] or 0,
        'low_stock': Product.objects.filter(stock__lte=LOW_STOCK_THRESHOLD).order_by('stock', 'name')[:6],
        'low_stock_count': Product.objects.filter(stock__lte=LOW_STOCK_THRESHOLD).count(),
        'recent_orders': Order.objects.select_related('user')[:6],
        'status_counts': [(label, status_counts[code], Order.BADGES[code]) for code, label in Order.STATUS_CHOICES],
    }
    return render(request, 'dashboard/overview.html', context)


# ---------- products ----------
@staff_required
def product_list(request):
    products = Product.objects.select_related('category')
    query = request.GET.get('q', '').strip()[:100]
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    category = request.GET.get('category', '')
    if category.isdigit():
        products = products.filter(category_id=int(category))
    stock = request.GET.get('stock', '')
    if stock == 'low':
        products = products.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD)
    elif stock == 'out':
        products = products.filter(stock=0)
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'dashboard/product_list.html', {
        'page': Paginator(products.order_by('name'), 12).get_page(request.GET.get('page')),
        'categories': Category.objects.all(),
        'query': query, 'selected_category': category, 'stock': stock,
        'querystring': params.urlencode(),
    })


@staff_required
def product_create(request):
    if not Category.objects.exists():
        messages.error(request, 'Create a category first, then add products.')
        return redirect('dashboard:category_create')
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f'Product "{product.name}" has been added.')
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/product_form.html', {'form': form, 'title': 'Add product'})


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Product "{product.name}" has been updated.')
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/product_form.html', {
        'form': form, 'title': f'Edit: {product.name}', 'product': product})


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f'Product "{name}" has been deleted.')
    return redirect('dashboard:product_list')


# ---------- categories ----------
@staff_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products'))
    return render(request, 'dashboard/category_list.html', {'categories': categories})


@staff_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        category = form.save()
        messages.success(request, f'Category "{category.name}" has been added.')
        return redirect('dashboard:category_list')
    return render(request, 'dashboard/category_form.html', {'form': form, 'title': 'Add category'})


@staff_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Category "{category.name}" has been updated.')
        return redirect('dashboard:category_list')
    return render(request, 'dashboard/category_form.html', {'form': form, 'title': f'Edit: {category.name}'})


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        messages.success(request, f'Category "{category.name}" has been deleted.')
    except ProtectedError:
        messages.error(request, f'"{category.name}" still has products. Move or delete them first.')
    return redirect('dashboard:category_list')


# ---------- orders ----------
@staff_required
def order_list(request):
    orders = Order.objects.select_related('user').prefetch_related('items')
    status = request.GET.get('status', '')
    if status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)
    else:
        status = ''
    query = request.GET.get('q', '').strip()[:60]
    if query:
        orders = orders.filter(Q(order_id__icontains=query) | Q(user__username__icontains=query))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'dashboard/order_list.html', {
        'page': Paginator(orders, 12).get_page(request.GET.get('page')),
        'status': status, 'query': query, 'statuses': Order.STATUS_CHOICES,
        'querystring': params.urlencode(),
    })


@staff_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user', 'shipping_address').prefetch_related('items'), order_id=order_id)
    form = None
    if order.next_statuses:
        form = OrderStatusForm(request.POST or None, order=order)
        if request.method == 'POST' and form.is_valid():
            try:
                order.set_status(form.cleaned_data['status'])
                messages.success(request, f'Order {order.order_id} is now {order.get_status_display().lower()}.')
            except ValueError as error:
                messages.error(request, str(error))
            return redirect('dashboard:order_detail', order_id=order.order_id)
    return render(request, 'dashboard/order_detail.html', {'order': order, 'form': form})


# ---------- customers ----------
@staff_required
def customer_list(request):
    customers = User.objects.filter(is_staff=False).annotate(
        order_count=Count('orders', distinct=True),
        total_spent=Sum('orders__total', filter=~Q(orders__status=Order.CANCELLED)),
    ).select_related('profile')
    query = request.GET.get('q', '').strip()[:60]
    if query:
        customers = customers.filter(
            Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'dashboard/customer_list.html', {
        'page': Paginator(customers.order_by('-date_joined'), 12).get_page(request.GET.get('page')),
        'query': query, 'querystring': params.urlencode(),
    })


# ---------- inventory ----------
@staff_required
def inventory(request):
    products = Product.objects.select_related('category')
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'low':
        products = products.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    value = ExpressionWrapper(F('price') * F('stock'), output_field=DecimalField(max_digits=14, decimal_places=2))
    totals = Product.objects.aggregate(units=Sum('stock'), value=Sum(value))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'dashboard/inventory.html', {
        'page': Paginator(products.order_by('stock', 'name'), 15).get_page(request.GET.get('page')),
        'stock_filter': stock_filter,
        'total_units': totals['units'] or 0,
        'total_value': totals['value'] or 0,
        'low_count': Product.objects.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD).count(),
        'out_count': Product.objects.filter(stock=0).count(),
        'threshold': LOW_STOCK_THRESHOLD,
        'querystring': params.urlencode(),
    })


@staff_required
@require_POST
def inventory_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        stock = int(request.POST.get('stock', ''))
        if not 0 <= stock <= MAX_STOCK:
            raise ValueError
    except ValueError:
        messages.error(request, f'Enter a stock number between 0 and {MAX_STOCK}.')
    else:
        product.stock = stock
        product.save(update_fields=['stock'])
        messages.success(request, f'Stock of "{product.name}" set to {stock}.')
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect('dashboard:inventory')
