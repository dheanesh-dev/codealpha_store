from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify

LOW_STOCK_THRESHOLD = 5

ICON_CHOICES = [
    ('fa-tag', 'Tag'),
    ('fa-laptop', 'Laptop'),
    ('fa-mobile-screen', 'Mobile'),
    ('fa-headphones', 'Headphones'),
    ('fa-shirt', 'Clothing'),
    ('fa-gem', 'Jewellery'),
    ('fa-glasses', 'Eyewear'),
    ('fa-blender', 'Kitchen'),
    ('fa-couch', 'Furniture'),
    ('fa-dumbbell', 'Fitness'),
    ('fa-futbol', 'Sports'),
    ('fa-book', 'Books'),
    ('fa-gamepad', 'Gaming'),
    ('fa-spa', 'Beauty'),
    ('fa-baby', 'Kids'),
]


def unique_slugify(instance, value):
    base = slugify(value)[:50] or 'item'
    slug, n = base, 2
    model = instance.__class__
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=60, unique=True, editable=False)
    description = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=40, choices=ICON_CHOICES, default='fa-tag')

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('store:product_list')}?category={self.slug}"


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, editable=False)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True)
    is_active = models.BooleanField(default=True, help_text='Inactive products are hidden from the store.')
    is_featured = models.BooleanField(default=False, help_text='Show on the homepage.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'name']
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name='product_price_gte_0'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:product_detail', args=[self.slug])

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= LOW_STOCK_THRESHOLD
