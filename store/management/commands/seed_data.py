from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from store.models import Category, Product

CATEGORIES = [
    ('Electronics', 'fa-headphones', 'Gadgets and everyday tech', ('#6d5dfc', '#3b82f6')),
    ('Fashion', 'fa-shirt', 'Clothing and footwear', ('#ff7a59', '#f43f5e')),
    ('Home & Kitchen', 'fa-blender', 'Make your home comfortable', ('#14b8a6', '#0ea5e9')),
    ('Accessories', 'fa-glasses', 'Finishing touches', ('#f59e0b', '#ef4444')),
    ('Sports & Fitness', 'fa-dumbbell', 'Gear for an active life', ('#22c55e', '#0d9488')),
]

# name, category, price, stock, emoji, featured, description
PRODUCTS = [
    ('Aero Wireless Headphones', 'Electronics', 2499, 25, '🎧', True,
     'Over-ear Bluetooth headphones with deep bass, soft ear cushions and up to 30 hours of battery life.'),
    ('Pulse Smart Watch', 'Electronics', 3999, 15, '⌚', True,
     'Fitness smart watch with heart-rate tracking, sleep monitoring, notifications and a bright AMOLED display.'),
    ('Nova Bluetooth Speaker', 'Electronics', 1799, 20, '🔊', False,
     'Portable water-resistant speaker with 360° sound and 12 hours of playtime.'),
    ('Volt 20000mAh Power Bank', 'Electronics', 1499, 40, '🔋', False,
     'High-capacity power bank with fast charging and dual USB output for all your devices.'),
    ('Orbit Wireless Mouse', 'Electronics', 799, 50, '🖱️', False,
     'Silent-click ergonomic wireless mouse with adjustable DPI and long battery life.'),
    ('Stride Running Shoes', 'Fashion', 2199, 30, '👟', True,
     'Lightweight, breathable running shoes with cushioned soles for daily training.'),
    ('Everyday Cotton T-Shirt', 'Fashion', 699, 60, '👕', False,
     'Soft 100% cotton crew-neck t-shirt with a relaxed fit. Easy to wear, easy to wash.'),
    ('Urban Denim Jacket', 'Fashion', 2899, 18, '🧥', True,
     'Classic mid-wash denim jacket with a modern cut. Pairs with almost anything.'),
    ('Voyager Travel Backpack', 'Fashion', 1599, 35, '🎒', False,
     'Water-resistant 30L backpack with a padded laptop sleeve and anti-theft back pocket.'),
    ('BrewMate Coffee Maker', 'Home & Kitchen', 3299, 12, '☕', True,
     'Programmable drip coffee maker with a 1.2L carafe and keep-warm plate.'),
    ('Glow LED Desk Lamp', 'Home & Kitchen', 899, 50, '💡', False,
     'Eye-friendly LED desk lamp with three colour modes and adjustable brightness.'),
    ('Cozy Throw Blanket', 'Home & Kitchen', 1199, 22, '🛋️', False,
     'Ultra-soft fleece throw blanket, perfect for the sofa or chilly evenings.'),
    ("Chef's Non-stick Pan Set", 'Home & Kitchen', 2499, 16, '🍳', False,
     'Three-piece non-stick pan set with stay-cool handles. Works on gas and induction.'),
    ('Aviator Sunglasses', 'Accessories', 799, 35, '🕶️', True,
     'Polarised UV400 aviator sunglasses with a lightweight metal frame.'),
    ('Classic Leather Wallet', 'Accessories', 999, 28, '👛', False,
     'Slim genuine-leather wallet with card slots, coin pocket and RFID protection.'),
    ('Minimal Analog Watch', 'Accessories', 1899, 4, '🕰️', False,
     'Clean, minimal analog watch with a stainless-steel case and leather strap. Limited stock.'),
    ('Silk Blend Scarf', 'Accessories', 649, 0, '🧣', False,
     'Lightweight silk-blend scarf in a soft pattern. Currently sold out.'),
    ('Iron Grip Dumbbell Set', 'Sports & Fitness', 3499, 10, '🏋️', True,
     'Adjustable dumbbell set with anti-slip grips. Train your whole body at home.'),
    ('ZenFlow Yoga Mat', 'Sports & Fitness', 999, 45, '🧘', False,
     'Extra-thick, non-slip yoga mat with a carrying strap.'),
    ('ProKick Football', 'Sports & Fitness', 1099, 30, '⚽', False,
     'Size-5 match football with a durable, water-resistant cover.'),
    ('Swift Skipping Rope', 'Sports & Fitness', 349, 70, '🪢', False,
     'Tangle-free speed rope with ball-bearing handles. Great for cardio.'),
    ('Hydra Steel Water Bottle', 'Sports & Fitness', 599, 55, '🥤', False,
     'Insulated stainless-steel bottle that keeps drinks cold for 24 hours.'),
]


def make_svg(emoji, c1, c2):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
        f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
        '<rect width="600" height="600" fill="url(#g)"/>'
        '<circle cx="480" cy="120" r="150" fill="#fff" opacity=".13"/>'
        '<circle cx="90" cy="520" r="180" fill="#fff" opacity=".10"/>'
        '<text x="300" y="360" font-size="230" text-anchor="middle" '
        'font-family="Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji, sans-serif">'
        f'{emoji}</text></svg>'
    )


DEMO_ADMIN = ('admin', 'admin@example.com', 'Admin@12345')
DEMO_CUSTOMER = ('demo', 'demo@example.com', 'Demo@12345')


class Command(BaseCommand):
    help = 'Load sample categories and products (safe to run more than once).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo-users', action='store_true',
            help='Also create a demo admin and a demo customer account for local evaluation.')

    def create_demo_users(self):
        from django.contrib.auth.models import User
        username, email, password = DEMO_ADMIN
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password, first_name='Admin')
            self.stdout.write(f'Demo admin created:    {username} / {password}')
        username, email, password = DEMO_CUSTOMER
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(username, email, password, first_name='Demo')
            self.stdout.write(f'Demo customer created: {username} / {password}')

    def handle(self, *args, **options):
        colors = {}
        categories = {}
        for name, icon, description, gradient in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=name, defaults={'icon': icon, 'description': description})
            categories[name] = category
            colors[name] = gradient

        created = 0
        for name, cat_name, price, stock, emoji, featured, description in PRODUCTS:
            product, was_created = Product.objects.get_or_create(
                name=name,
                defaults={'category': categories[cat_name], 'price': price, 'stock': stock,
                          'is_featured': featured, 'description': description})
            if was_created:
                created += 1
            if not product.image:
                svg = make_svg(emoji, *colors[cat_name])
                product.image.save(f'{product.slug}.svg', ContentFile(svg.encode('utf-8')), save=True)

        self.stdout.write(self.style.SUCCESS(
            f'{len(CATEGORIES)} categories ready, {created} new products added '
            f'({Product.objects.count()} total).'))
        if options['demo_users']:
            self.create_demo_users()
