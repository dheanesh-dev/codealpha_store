import secrets
import string

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import phone_validator
from store.models import Product

pincode_validator = RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit PIN code.')


class ShippingAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=16, validators=[phone_validator])
    address_line1 = models.CharField('Address line 1', max_length=200)
    address_line2 = models.CharField('Address line 2 (optional)', max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField('PIN code', max_length=6, validators=[pincode_validator])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'shipping addresses'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name}, {self.city} - {self.pincode}'

    def as_lines(self):
        lines = [self.address_line1, self.address_line2, f'{self.city}, {self.state} - {self.pincode}']
        return [line for line in lines if line]


def generate_order_id():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(5))
        order_id = f"LM-{timezone.localdate():%y%m%d}-{code}"
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id


class Order(models.Model):
    PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED = 'PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]
    ALLOWED_TRANSITIONS = {
        PENDING: (CONFIRMED, CANCELLED),
        CONFIRMED: (SHIPPED, CANCELLED),
        SHIPPED: (DELIVERED,),
        DELIVERED: (),
        CANCELLED: (),
    }
    BADGES = {PENDING: 'warning', CONFIRMED: 'info', SHIPPED: 'info', DELIVERED: 'success', CANCELLED: 'danger'}

    order_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.PROTECT, related_name='orders')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=Q(total__gte=0), name='order_total_gte_0'),
        ]

    def __str__(self):
        return self.order_id

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = generate_order_id()
        super().save(*args, **kwargs)

    @property
    def badge(self):
        return self.BADGES.get(self.status, 'muted')

    @property
    def can_cancel(self):
        return self.CANCELLED in self.ALLOWED_TRANSITIONS.get(self.status, ())

    @property
    def next_statuses(self):
        labels = dict(self.STATUS_CHOICES)
        return [(code, labels[code]) for code in self.ALLOWED_TRANSITIONS.get(self.status, ())]

    @property
    def timeline(self):
        if self.status == self.CANCELLED:
            return []
        flow = [(self.PENDING, 'Order placed'), (self.CONFIRMED, 'Confirmed'),
                (self.SHIPPED, 'Shipped'), (self.DELIVERED, 'Delivered')]
        current = [code for code, _ in flow].index(self.status)
        return [{'label': label, 'done': i <= current, 'current': i == current}
                for i, (_, label) in enumerate(flow)]

    def set_status(self, new_status):
        """Change the status safely. Cancelling returns the items to stock."""
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if new_status not in self.ALLOWED_TRANSITIONS.get(order.status, ()):
                labels = dict(self.STATUS_CHOICES)
                raise ValueError(
                    f'An order that is {labels[order.status].lower()} cannot be changed to '
                    f'{labels.get(new_status, new_status).lower()}.')
            if new_status == self.CANCELLED:
                for item in order.items.all():
                    if item.product_id:
                        Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
        self.status = new_status
        self.updated_at = order.updated_at


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name='orderitem_quantity_gte_1'),
        ]

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'

    @property
    def line_total(self):
        return self.unit_price * self.quantity
