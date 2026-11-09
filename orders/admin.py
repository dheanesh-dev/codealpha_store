from django.contrib import admin

from .models import Order, OrderItem, ShippingAddress


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'unit_price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'total', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('order_id', 'user__username')
    inlines = [OrderItemInline]


admin.site.register(ShippingAddress)
