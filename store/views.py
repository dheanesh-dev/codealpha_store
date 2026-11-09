from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product

SORTS = {
    'newest': ('Newest first', '-created_at'),
    'price_asc': ('Price: low to high', 'price'),
    'price_desc': ('Price: high to low', '-price'),
    'name': ('Name: A to Z', 'name'),
}


def _parse_price(value):
    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError):
        return None
    return price if price.is_finite() and price >= 0 else None


def home(request):
    active = Product.objects.filter(is_active=True).select_related('category')
    context = {
        'featured': active.filter(is_featured=True)[:8],
        'new_arrivals': active[:4],
        'categories': Category.objects.annotate(
            product_count=Count('products', filter=Q(products__is_active=True))),
    }
    return render(request, 'store/home.html', context)


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category')

    query = request.GET.get('q', '').strip()[:100]
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query))

    category_slug = request.GET.get('category', '').strip()
    current_category = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug).first()
        products = products.filter(category__slug=category_slug)

    min_price = _parse_price(request.GET.get('min_price'))
    max_price = _parse_price(request.GET.get('max_price'))
    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)

    only_in_stock = request.GET.get('in_stock') == '1'
    if only_in_stock:
        products = products.filter(stock__gt=0)

    sort = request.GET.get('sort', 'newest')
    if sort not in SORTS:
        sort = 'newest'
    products = products.order_by(SORTS[sort][1], 'name')

    page = Paginator(products, 9).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'store/product_list.html', {
        'page': page,
        'query': query,
        'categories': Category.objects.all(),
        'current_category': current_category,
        'selected_category': category_slug,
        'min_price': request.GET.get('min_price', '') if min_price is not None else '',
        'max_price': request.GET.get('max_price', '') if max_price is not None else '',
        'only_in_stock': only_in_stock,
        'sort': sort,
        'sorts': [(key, label) for key, (label, _) in SORTS.items()],
        'querystring': params.urlencode(),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category'), slug=slug, is_active=True)
    related = Product.objects.filter(
        is_active=True, category=product.category).exclude(pk=product.pk)[:4]
    return render(request, 'store/product_detail.html', {
        'product': product,
        'related': related,
        'max_quantity': min(product.stock, 99),
    })
