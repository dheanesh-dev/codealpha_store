import threading
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from store.models import Product
from store.tests import make_product

from .models import Order, OrderItem, ShippingAddress
from .services import CheckoutError, place_order

PASSWORD = 'Sup3r-Secret!42'
ADDRESS = {'full_name': 'Amy Ray', 'phone': '9876543210', 'address_line1': '12 Main Road',
           'address_line2': '', 'city': 'Chennai', 'state': 'Tamil Nadu', 'pincode': '600001'}


class OrderTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('amy', 'amy@example.com', PASSWORD, first_name='Amy')
        self.client.login(username='amy', password=PASSWORD)
        self.lamp = make_product('Lamp', '200', 5)
        self.mug = make_product('Mug', '50', 10)

    def fill_cart(self, user=None, **quantities):
        cart = Cart.objects.get_or_create(user=user or self.user)[0]
        for product, qty in quantities.items():
            CartItem.objects.create(cart=cart, product=getattr(self, product), quantity=qty)
        return cart


class CheckoutTests(OrderTestBase):
    def test_checkout_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('orders:checkout')).status_code, 302)

    def test_empty_cart_redirects(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('cart:detail'))

    def test_checkout_page_shows_summary(self):
        self.fill_cart(lamp=2, mug=1)
        response = self.client.get(reverse('orders:checkout'))
        self.assertContains(response, '₹450.00')
        self.assertContains(response, 'Delivery address')

    def test_successful_order(self):
        self.fill_cart(lamp=2, mug=3)
        response = self.client.post(reverse('orders:checkout'), ADDRESS)
        order = Order.objects.get()
        self.assertRedirects(response, reverse('orders:confirmation', args=[order.order_id]))
        self.assertEqual(order.total, Decimal('550.00'))
        self.assertEqual(order.status, Order.PENDING)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.shipping_address.city, 'Chennai')
        self.lamp.refresh_from_db(); self.mug.refresh_from_db()
        self.assertEqual((self.lamp.stock, self.mug.stock), (3, 7))
        self.assertFalse(CartItem.objects.exists())

    def test_order_ids_are_unique_and_formatted(self):
        self.fill_cart(lamp=1)
        self.client.post(reverse('orders:checkout'), ADDRESS)
        self.fill_cart(mug=1)
        self.client.post(reverse('orders:checkout'), ADDRESS)
        ids = list(Order.objects.values_list('order_id', flat=True))
        self.assertEqual(len(set(ids)), 2)
        self.assertTrue(all(i.startswith('LM-') for i in ids))

    def test_price_snapshot_survives_price_change(self):
        self.fill_cart(lamp=1)
        self.client.post(reverse('orders:checkout'), ADDRESS)
        Product.objects.filter(pk=self.lamp.pk).update(price=Decimal('999'))
        item = OrderItem.objects.get()
        self.assertEqual(item.unit_price, Decimal('200.00'))
        self.assertEqual(Order.objects.get().total, Decimal('200.00'))

    def test_invalid_address_rejected(self):
        self.fill_cart(lamp=1)
        bad = dict(ADDRESS, pincode='12', phone='abc')
        response = self.client.post(reverse('orders:checkout'), bad)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid 6-digit PIN')
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.count(), 1)

    def test_order_blocked_when_stock_dropped(self):
        self.fill_cart(lamp=4)
        Product.objects.filter(pk=self.lamp.pk).update(stock=2)
        response = self.client.post(reverse('orders:checkout'), ADDRESS)
        self.assertRedirects(response, reverse('cart:detail'))
        self.assertFalse(Order.objects.exists())
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 2)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_order_blocked_for_inactive_product(self):
        self.fill_cart(lamp=1)
        Product.objects.filter(pk=self.lamp.pk).update(is_active=False)
        with self.assertRaises(CheckoutError):
            place_order(self.user, ADDRESS)
        self.assertFalse(Order.objects.exists())

    def test_failed_order_is_fully_rolled_back(self):
        self.fill_cart(mug=2, lamp=9)  # lamp exceeds stock of 5
        with self.assertRaises(CheckoutError):
            place_order(self.user, ADDRESS)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(ShippingAddress.objects.exists())
        self.mug.refresh_from_db()
        self.assertEqual(self.mug.stock, 10)

    def test_cart_page_blocks_checkout_when_over_stock(self):
        self.fill_cart(lamp=4)
        Product.objects.filter(pk=self.lamp.pk).update(stock=1)
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'Fix cart issues')

    def test_two_buyers_cannot_oversell(self):
        other = User.objects.create_user('bob', 'bob@example.com', PASSWORD)
        self.fill_cart(lamp=4)
        self.fill_cart(user=other, lamp=4)
        place_order(self.user, ADDRESS)
        with self.assertRaises(CheckoutError):
            place_order(other, ADDRESS)
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 1)


class OrderViewTests(OrderTestBase):
    def place(self, **quantities):
        self.fill_cart(**quantities)
        self.client.post(reverse('orders:checkout'), ADDRESS)
        return Order.objects.first()

    def test_confirmation_and_detail_pages(self):
        order = self.place(lamp=1)
        self.assertContains(self.client.get(reverse('orders:confirmation', args=[order.order_id])), 'Order confirmed')
        detail = self.client.get(reverse('orders:detail', args=[order.order_id]))
        self.assertContains(detail, order.order_id)
        self.assertContains(detail, 'Order tracking')

    def test_order_history_lists_only_own_orders(self):
        mine = self.place(lamp=1)
        other = User.objects.create_user('bob', 'bob@example.com', PASSWORD)
        self.fill_cart(user=other, mug=1)
        place_order(other, ADDRESS)
        response = self.client.get(reverse('orders:history'))
        self.assertContains(response, mine.order_id)
        self.assertEqual(response.context['page'].paginator.count, 1)

    def test_cannot_view_someone_elses_order(self):
        other = User.objects.create_user('bob', 'bob@example.com', PASSWORD)
        self.fill_cart(user=other, mug=1)
        theirs = place_order(other, ADDRESS)
        self.assertEqual(self.client.get(reverse('orders:detail', args=[theirs.order_id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('orders:cancel', args=[theirs.order_id])).status_code, 404)

    def test_history_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('orders:history')).status_code, 302)

    def test_customer_can_cancel_pending_order_and_stock_returns(self):
        order = self.place(lamp=2)
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 3)
        self.client.post(reverse('orders:cancel', args=[order.order_id]))
        order.refresh_from_db(); self.lamp.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertEqual(self.lamp.stock, 5)

    def test_cancel_twice_does_not_restock_twice(self):
        order = self.place(lamp=2)
        self.client.post(reverse('orders:cancel', args=[order.order_id]))
        self.client.post(reverse('orders:cancel', args=[order.order_id]))
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 5)

    def test_shipped_order_cannot_be_cancelled(self):
        order = self.place(lamp=1)
        order.set_status(Order.CONFIRMED); order.set_status(Order.SHIPPED)
        self.client.post(reverse('orders:cancel', args=[order.order_id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.SHIPPED)

    def test_status_transitions(self):
        order = self.place(lamp=1)
        with self.assertRaises(ValueError):
            order.set_status(Order.DELIVERED)
        for status in (Order.CONFIRMED, Order.SHIPPED, Order.DELIVERED):
            order.set_status(status)
        with self.assertRaises(ValueError):
            order.set_status(Order.CANCELLED)

    def test_timeline_progress(self):
        order = self.place(lamp=1)
        order.set_status(Order.CONFIRMED)
        done = [s['label'] for s in order.timeline if s['done']]
        self.assertEqual(done, ['Order placed', 'Confirmed'])
