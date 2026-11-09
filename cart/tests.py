from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from store.tests import make_product

from .models import Cart, CartItem


class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('amy', 'amy@example.com', 'Sup3r-Secret!42')
        self.client.login(username='amy', password='Sup3r-Secret!42')
        self.product = make_product('Lamp', '200', 5)

    def add(self, product=None, quantity=1, **extra):
        product = product or self.product
        return self.client.post(reverse('cart:add', args=[product.id]), {'quantity': quantity}, **extra)

    def item(self):
        return CartItem.objects.get(cart__user=self.user, product=self.product)

    def test_anonymous_add_redirects_to_login(self):
        self.client.logout()
        response = self.add(HTTP_REFERER='http://testserver/shop/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/?next=', response['Location'])
        self.assertEqual(CartItem.objects.count(), 0)

    def test_anonymous_ajax_add_returns_401(self):
        self.client.logout()
        response = self.add(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 401)
        self.assertIn('login_url', response.json())

    def test_cart_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('cart:detail')).status_code, 302)

    def test_add_creates_item_and_merges(self):
        self.add(quantity=2)
        self.add(quantity=1)
        self.assertEqual(self.item().quantity, 3)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_ajax_add_returns_count(self):
        response = self.add(quantity=2, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['count'], 2)
        self.assertTrue(response.json()['ok'])

    def test_cannot_add_more_than_stock(self):
        response = self.add(quantity=6, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_cannot_exceed_stock_across_adds(self):
        self.add(quantity=4)
        response = self.add(quantity=2, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.item().quantity, 4)

    def test_out_of_stock_and_inactive_products(self):
        sold_out = make_product('Gone', '10', 0)
        self.assertEqual(self.add(sold_out, HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code, 400)
        hidden = make_product('Hidden', '10', 5, is_active=False)
        self.assertEqual(self.add(hidden).status_code, 404)

    def test_invalid_quantities_rejected(self):
        for bad in ('0', '-3', 'abc', '1000'):
            response = self.add(quantity=bad, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_increase_decrease_and_remove_on_zero(self):
        self.add(quantity=2)
        item = self.item()
        url = reverse('cart:update', args=[item.id])
        self.client.post(url, {'action': 'inc'})
        self.assertEqual(self.item().quantity, 3)
        self.client.post(url, {'action': 'dec'})
        self.client.post(url, {'action': 'dec'})
        self.assertEqual(self.item().quantity, 1)
        self.client.post(url, {'action': 'dec'})
        self.assertFalse(CartItem.objects.exists())

    def test_increase_blocked_at_stock_limit(self):
        self.add(quantity=5)
        self.client.post(reverse('cart:update', args=[self.item().id]), {'action': 'inc'})
        self.assertEqual(self.item().quantity, 5)

    def test_set_quantity(self):
        self.add()
        url = reverse('cart:update', args=[self.item().id])
        self.client.post(url, {'action': 'set', 'quantity': '4'})
        self.assertEqual(self.item().quantity, 4)
        self.client.post(url, {'action': 'set', 'quantity': '99'})
        self.assertEqual(self.item().quantity, 4)
        self.client.post(url, {'action': 'set', 'quantity': 'x'})
        self.assertEqual(self.item().quantity, 4)

    def test_remove_item(self):
        self.add()
        self.client.post(reverse('cart:remove', args=[self.item().id]))
        self.assertFalse(CartItem.objects.exists())

    def test_cannot_modify_another_users_cart(self):
        other = User.objects.create_user('eve', 'eve@example.com', 'Sup3r-Secret!42')
        cart = Cart.objects.create(user=other)
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.assertEqual(self.client.post(reverse('cart:remove', args=[item.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('cart:update', args=[item.id]), {'action': 'inc'}).status_code, 404)

    def test_totals_on_cart_page(self):
        self.add(quantity=3)
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, '₹600.00')
        self.assertEqual(response.context['subtotal'], 600)

    def test_add_requires_post(self):
        self.assertEqual(self.client.get(reverse('cart:add', args=[self.product.id])).status_code, 405)

    def test_cart_badge_count(self):
        self.add(quantity=3)
        response = self.client.get(reverse('store:home'))
        self.assertEqual(response.context['cart_count'], 3)
