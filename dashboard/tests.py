import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from cart.models import Cart, CartItem
from orders.models import Order
from orders.services import place_order
from orders.tests import ADDRESS
from store.models import Category, Product
from store.tests import make_product

PASSWORD = 'Sup3r-Secret!42'


def png_bytes(size=(20, 20)):
    buf = BytesIO()
    Image.new('RGB', size, 'red').save(buf, 'PNG')
    return buf.getvalue()


class DashboardTestBase(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, True)
        self.staff = User.objects.create_user('boss', 'boss@example.com', PASSWORD, is_staff=True)
        self.customer = User.objects.create_user('amy', 'amy@example.com', PASSWORD)
        self.category = Category.objects.create(name='Gadgets')
        self.product = make_product('Lamp', '200', 5, self.category)
        self.client.login(username='boss', password=PASSWORD)

    def make_order(self, qty=2):
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=qty)
        return place_order(self.customer, ADDRESS)


class PermissionTests(DashboardTestBase):
    URLS = ['dashboard:overview', 'dashboard:product_list', 'dashboard:product_create', 'dashboard:category_list',
            'dashboard:category_create', 'dashboard:order_list', 'dashboard:customer_list', 'dashboard:inventory']

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        for name in self.URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_customer_gets_403(self):
        self.client.login(username='amy', password=PASSWORD)
        for name in self.URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_customer_cannot_post_admin_actions(self):
        self.client.login(username='amy', password=PASSWORD)
        self.assertEqual(self.client.post(reverse('dashboard:product_delete', args=[self.product.pk])).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(self.client.post(reverse('dashboard:inventory_update', args=[self.product.pk]), {'stock': 99}).status_code, 403)

    def test_staff_can_open_all_pages(self):
        for name in self.URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class ProductManagementTests(DashboardTestBase):
    def form_data(self, **extra):
        data = {'name': 'Desk Fan', 'category': self.category.pk, 'description': 'Cool breeze',
                'price': '1299.50', 'stock': '12', 'is_active': 'on'}
        data.update(extra)
        return data

    def test_add_product_with_image(self):
        image = SimpleUploadedFile('fan.png', png_bytes(), content_type='image/png')
        response = self.client.post(reverse('dashboard:product_create'), self.form_data(image=image))
        self.assertRedirects(response, reverse('dashboard:product_list'))
        product = Product.objects.get(name='Desk Fan')
        self.assertTrue(product.image.name.startswith('products/'))
        self.assertEqual(product.slug, 'desk-fan')
        self.assertTrue(self.client.get(product.get_absolute_url()).status_code, 200)

    def test_non_image_upload_rejected(self):
        fake = SimpleUploadedFile('x.png', b'not really an image', content_type='image/png')
        response = self.client.post(reverse('dashboard:product_create'), self.form_data(image=fake))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name='Desk Fan').exists())

    def test_invalid_price_rejected(self):
        for bad in ('0', '-5', 'abc'):
            response = self.client.post(reverse('dashboard:product_create'), self.form_data(price=bad))
            self.assertEqual(response.status_code, 200, bad)
        self.assertFalse(Product.objects.filter(name='Desk Fan').exists())

    def test_edit_product(self):
        response = self.client.post(reverse('dashboard:product_edit', args=[self.product.pk]),
                                    self.form_data(name='Lamp Pro', price='250'))
        self.assertRedirects(response, reverse('dashboard:product_list'))
        self.product.refresh_from_db()
        self.assertEqual((self.product.name, self.product.price), ('Lamp Pro', 250))

    def test_delete_product_keeps_order_history(self):
        order = self.make_order()
        self.client.post(reverse('dashboard:product_delete', args=[self.product.pk]))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        item = order.items.get()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, 'Lamp')

    def test_delete_requires_post(self):
        self.assertEqual(self.client.get(reverse('dashboard:product_delete', args=[self.product.pk])).status_code, 405)

    def test_product_list_search_and_stock_filter(self):
        make_product('Empty Box', '5', 0, self.category)
        response = self.client.get(reverse('dashboard:product_list'), {'stock': 'out'})
        self.assertContains(response, 'Empty Box')
        self.assertNotContains(response, '>Lamp<')
        response = self.client.get(reverse('dashboard:product_list'), {'q': 'lamp'})
        self.assertContains(response, 'Lamp')


class CategoryManagementTests(DashboardTestBase):
    def test_add_edit_delete_category(self):
        self.client.post(reverse('dashboard:category_create'), {'name': 'Toys', 'description': 'Fun', 'icon': 'fa-baby'})
        toys = Category.objects.get(name='Toys')
        self.assertEqual(toys.slug, 'toys')
        self.client.post(reverse('dashboard:category_edit', args=[toys.pk]), {'name': 'Kids Toys', 'description': '', 'icon': 'fa-baby'})
        toys.refresh_from_db()
        self.assertEqual(toys.name, 'Kids Toys')
        self.client.post(reverse('dashboard:category_delete', args=[toys.pk]))
        self.assertFalse(Category.objects.filter(pk=toys.pk).exists())

    def test_category_with_products_cannot_be_deleted(self):
        response = self.client.post(reverse('dashboard:category_delete', args=[self.category.pk]), follow=True)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
        self.assertContains(response, 'still has products')

    def test_duplicate_category_name_rejected(self):
        response = self.client.post(reverse('dashboard:category_create'), {'name': 'Gadgets', 'icon': 'fa-tag'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Category.objects.filter(name='Gadgets').count(), 1)

    def test_invalid_icon_rejected(self):
        response = self.client.post(reverse('dashboard:category_create'), {'name': 'Bad', 'icon': '"><script>'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Category.objects.filter(name='Bad').exists())


class OrderManagementTests(DashboardTestBase):
    def test_orders_list_and_detail(self):
        order = self.make_order()
        self.assertContains(self.client.get(reverse('dashboard:order_list')), order.order_id)
        self.assertContains(self.client.get(reverse('dashboard:order_detail', args=[order.order_id])), 'Update status')

    def test_filter_orders_by_status(self):
        order = self.make_order()
        response = self.client.get(reverse('dashboard:order_list'), {'status': 'SHIPPED'})
        self.assertNotContains(response, order.order_id)

    def test_update_status_through_workflow(self):
        order = self.make_order()
        url = reverse('dashboard:order_detail', args=[order.order_id])
        for status in ('CONFIRMED', 'SHIPPED', 'DELIVERED'):
            self.client.post(url, {'status': status})
            order.refresh_from_db()
            self.assertEqual(order.status, status)
        self.assertNotContains(self.client.get(url), 'Update status</button>')

    def test_invalid_status_rejected(self):
        order = self.make_order()
        self.client.post(reverse('dashboard:order_detail', args=[order.order_id]), {'status': 'DELIVERED'})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PENDING)

    def test_cancelling_restocks(self):
        order = self.make_order(qty=3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.client.post(reverse('dashboard:order_detail', args=[order.order_id]), {'status': 'CANCELLED'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)


class CustomerAndInventoryTests(DashboardTestBase):
    def test_customer_list_excludes_staff_and_counts_orders(self):
        self.make_order()
        response = self.client.get(reverse('dashboard:customer_list'))
        self.assertContains(response, 'amy')
        self.assertNotContains(response, '@boss')
        row = list(response.context['page'])[0]
        self.assertEqual(row.order_count, 1)
        self.assertEqual(row.total_spent, 400)

    def test_customer_search(self):
        self.assertNotContains(self.client.get(reverse('dashboard:customer_list'), {'q': 'zzz'}), '@amy')

    def test_inventory_update(self):
        response = self.client.post(reverse('dashboard:inventory_update', args=[self.product.pk]),
                                    {'stock': '42', 'next': reverse('dashboard:inventory')})
        self.assertRedirects(response, reverse('dashboard:inventory'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 42)

    def test_inventory_rejects_bad_values(self):
        for bad in ('-1', 'abc', '', '999999999'):
            self.client.post(reverse('dashboard:inventory_update', args=[self.product.pk]), {'stock': bad})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_inventory_ignores_external_redirect(self):
        response = self.client.post(reverse('dashboard:inventory_update', args=[self.product.pk]),
                                    {'stock': '7', 'next': 'https://evil.example.com/'})
        self.assertRedirects(response, reverse('dashboard:inventory'))

    def test_inventory_summary_numbers(self):
        make_product('Empty', '10', 0, self.category)
        response = self.client.get(reverse('dashboard:inventory'))
        self.assertEqual(response.context['out_count'], 1)
        self.assertEqual(response.context['total_units'], 5)
        self.assertEqual(response.context['total_value'], 1000)

    def test_overview_numbers(self):
        self.make_order()
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.context['order_count'], 1)
        self.assertEqual(response.context['revenue'], 400)
        self.assertEqual(response.context['customer_count'], 1)
