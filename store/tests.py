from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


def make_product(name='Widget', price='100.00', stock=10, category=None, **kwargs):
    category = category or Category.objects.get_or_create(name='Gadgets')[0]
    return Product.objects.create(name=name, category=category, price=Decimal(price), stock=stock,
                                  description=kwargs.pop('description', 'A product'), **kwargs)


class CatalogTests(TestCase):
    def setUp(self):
        self.electronics = Category.objects.create(name='Electronics')
        self.fashion = Category.objects.create(name='Fashion')
        self.phone = make_product('Phone', '500', 5, self.electronics, is_featured=True)
        self.shirt = make_product('Blue Shirt', '50', 20, self.fashion)
        self.hidden = make_product('Hidden Thing', '10', 5, self.fashion, is_active=False)
        self.sold_out = make_product('Old Radio', '70', 0, self.electronics)

    def test_home_shows_featured_and_categories(self):
        response = self.client.get(reverse('store:home'))
        self.assertContains(response, 'Phone')
        self.assertContains(response, 'Electronics')

    def test_listing_hides_inactive_products(self):
        response = self.client.get(reverse('store:product_list'))
        self.assertContains(response, 'Phone')
        self.assertNotContains(response, 'Hidden Thing')

    def test_search(self):
        response = self.client.get(reverse('store:product_list'), {'q': 'shirt'})
        self.assertContains(response, 'Blue Shirt')
        self.assertNotContains(response, 'Phone')

    def test_search_no_results(self):
        response = self.client.get(reverse('store:product_list'), {'q': 'zzzz'})
        self.assertContains(response, 'No products match')

    def test_category_filter(self):
        response = self.client.get(reverse('store:product_list'), {'category': self.fashion.slug})
        self.assertContains(response, 'Blue Shirt')
        self.assertNotContains(response, 'Phone')

    def test_price_filter(self):
        response = self.client.get(reverse('store:product_list'), {'min_price': '60', 'max_price': '600'})
        names = [p.name for p in response.context['page']]
        self.assertCountEqual(names, ['Phone', 'Old Radio'])

    def test_invalid_price_filter_is_ignored(self):
        response = self.client.get(reverse('store:product_list'), {'min_price': 'abc', 'max_price': '-5'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 3)

    def test_in_stock_filter(self):
        response = self.client.get(reverse('store:product_list'), {'in_stock': '1'})
        self.assertNotContains(response, 'Old Radio')

    def test_sorting(self):
        asc = self.client.get(reverse('store:product_list'), {'sort': 'price_asc'})
        self.assertEqual([p.name for p in asc.context['page']], ['Blue Shirt', 'Old Radio', 'Phone'])
        desc = self.client.get(reverse('store:product_list'), {'sort': 'price_desc'})
        self.assertEqual([p.name for p in desc.context['page']], ['Phone', 'Old Radio', 'Blue Shirt'])

    def test_invalid_sort_falls_back(self):
        self.assertEqual(self.client.get(reverse('store:product_list'), {'sort': 'evil'}).status_code, 200)

    def test_pagination(self):
        for i in range(10):
            make_product(f'Extra {i}', '5', 5, self.fashion)
        response = self.client.get(reverse('store:product_list'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page'].has_previous())

    def test_detail_page(self):
        response = self.client.get(self.phone.get_absolute_url())
        self.assertContains(response, 'Phone')
        self.assertContains(response, '₹500.00')
        self.assertContains(response, 'Only 5 left')

    def test_detail_sold_out(self):
        response = self.client.get(self.sold_out.get_absolute_url())
        self.assertContains(response, 'Out of stock')

    def test_inactive_product_detail_is_404(self):
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)

    def test_slugs_are_unique(self):
        a = make_product('Same Name', '1', 1, self.fashion)
        b = make_product('Same Name', '1', 1, self.fashion)
        self.assertNotEqual(a.slug, b.slug)

    def test_negative_price_blocked_by_database(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(name='Bad', category=self.fashion, price=Decimal('-1'), description='x')


class SeedTests(TestCase):
    def test_seed_is_idempotent_and_creates_images(self):
        import shutil, tempfile
        from django.test import override_settings
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=tmp):
                call_command('seed_data', verbosity=0)
                count = Product.objects.count()
                call_command('seed_data', verbosity=0)
                self.assertEqual(Product.objects.count(), count)
                self.assertGreaterEqual(count, 20)
                self.assertFalse(Product.objects.filter(image='').exists())
                self.assertTrue(Product.objects.filter(stock=0).exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class DemoUsersTests(TestCase):
    def test_demo_users_created_once_and_work(self):
        import shutil, tempfile
        from django.contrib.auth.models import User
        from django.test import override_settings
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=tmp):
                call_command('seed_data', '--demo-users', verbosity=0)
                call_command('seed_data', '--demo-users', verbosity=0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(self.client.login(username='admin', password='Admin@12345'))
        self.assertEqual(self.client.get(reverse('dashboard:overview')).status_code, 200)
        self.client.logout()
        self.assertTrue(self.client.login(username='demo', password='Demo@12345'))
        self.assertEqual(self.client.get(reverse('dashboard:overview')).status_code, 403)

    def test_no_users_without_flag(self):
        import shutil, tempfile
        from django.contrib.auth.models import User
        from django.test import override_settings
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=tmp):
                call_command('seed_data', verbosity=0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(User.objects.count(), 0)
