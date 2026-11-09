# Lumio – Full Stack E-commerce Store

A complete e-commerce web application built with **Django, HTML, CSS, JavaScript and SQLite** for the
CodeAlpha Full Stack Development Internship.

## Features

| Area | What is included |
|---|---|
| **Authentication** | Register, log in, log out, password validation and hashing, user profile (view and edit), login-protected pages |
| **Products** | Listing, product details, product images, categories, search, price and stock filters, sorting, pagination, stock badges |
| **Cart** | Add, remove, increase/decrease quantity, automatic subtotal and total, stock validation, cart badge updated without page reload |
| **Orders** | Checkout with delivery address, order summary, unique order ID (e.g. `LM-261109-Y12A3`), confirmation page, order history, status tracking timeline, cancel before shipping |
| **Admin dashboard** | Overview statistics, add/edit/delete products, manage categories, view customers, view and manage orders, update order status, inventory management with inline stock editing |
| **UI/UX** | Responsive layout (desktop, tablet, mobile), hero banner, featured products, category cards, hover effects, scroll animations, toast notifications, Font Awesome icons |
| **Security** | Django password hashing, CSRF protection on every form, server-side validation, staff-only dashboard (403 for others), atomic order processing with row locking, secrets kept out of the code |

## Tech stack

Python · Django 5 · SQLite · HTML5 · CSS3 · JavaScript (vanilla) · Pillow (image uploads) · Font Awesome

## Quick start (for evaluators)

Requires Python 3.10+.

**Windows, easiest:** double-click **`run_windows.bat`**. It installs everything, creates the database, loads sample
products and demo accounts, and starts the website. Then open **http://127.0.0.1:8000/**

**Or run the commands yourself** in the project folder (the one that contains `manage.py`):

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data --demo-users
python manage.py runserver
```

### Demo accounts (local testing only)

| Role | Username | Password | Where to use it |
|---|---|---|---|
| Admin | `admin` | `Admin@12345` | http://127.0.0.1:8000/dashboard/ |
| Customer | `demo` | `Demo@12345` | http://127.0.0.1:8000/ |

You can also register your own customer account on the site. The demo accounts only exist in your local
database and are created by `seed_data --demo-users`. Do not use them for a real deployment.

| Page | URL |
|---|---|
| Store | http://127.0.0.1:8000/ |
| Admin dashboard (staff only) | http://127.0.0.1:8000/dashboard/ |
| Django admin (backup) | http://127.0.0.1:8000/admin/ |

> Font Awesome icons and Google Fonts load from a CDN, so an internet connection is needed for the full look.
> Use a virtual environment if you prefer: `python -m venv venv`, then `venv\Scripts\activate` (Windows).
> To create your own admin instead of the demo one: `python manage.py createsuperuser`.

## Project structure

```
codealpha_store/
├── manage.py
├── requirements.txt
├── config/            settings, root urls, shared form styling
├── accounts/          registration, login, profile
├── store/             categories, products, home, listing, details, seed_data command
├── cart/              cart and cart items
├── orders/            checkout, orders, order items, shipping addresses, order service
├── dashboard/         staff-only management UI
├── templates/         base layout and shared partials
└── static/            css/style.css, css/dashboard.css, js/main.js
```

## Database models

`User` (Django) · `Profile` · `Category` · `Product` · `Cart` · `CartItem` · `ShippingAddress` · `Order` · `OrderItem`

- Database constraints: price ≥ 0, cart quantity ≥ 1, order quantity ≥ 1, order total ≥ 0, one row per product in a cart, unique slugs and order IDs.
- Order items store a **snapshot** of product name and price, so history stays correct if a product is edited or deleted.

## How order processing stays safe

Checkout runs inside one database transaction: the products are locked, stock is checked again, the order and
its items are created, stock is reduced and the cart is emptied. If anything fails, nothing is saved.
Cancelling an order (customer or admin) returns the items to stock exactly once.

Order status flow: `Pending → Confirmed → Shipped → Delivered`, with `Cancelled` possible from Pending or Confirmed.

## Automated tests

```bash
python manage.py test
```

90 tests cover registration and login, product listing/search/filter/sort, cart rules, stock limits, checkout,
order history, order status changes, dashboard permissions, product/category management and inventory.

## Manual testing checklist

1. Register with a valid password (a weak one such as `12345678` must be rejected with a clear message).
2. Log out and log in again. Open **My account** and edit your profile.
3. Browse **Shop**, search for `watch`, filter by category and price, sort by price, open a product page.
4. Click **Add** on a product while logged out. You are sent to login and brought back afterwards.
5. Add products to the cart, change quantities with `+` / `−`, and try to exceed the stock (it must be refused).
6. Remove an item. Check that subtotal and total update.
7. Checkout with an invalid PIN code (must show an error), then with valid details. See the confirmation page.
8. Open **My orders**, view the order and its tracking timeline. Cancel a pending order and confirm stock returns.
9. Log in as `admin` (see demo accounts) and open `/dashboard/`. Add a product with an image, edit it, then delete it.
10. Add, edit and delete a category (a category that still has products cannot be deleted).
11. Open **Orders**, change an order to Confirmed → Shipped → Delivered. Check the customer sees the new status.
12. Open **Customers** and **Inventory**, and update a stock value.
13. As a normal customer, open `/dashboard/`. You must get "403 Access denied".

## Configuration and secrets

No secret is stored in the code. Copy `.env.example` to `.env` to set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` or
`DJANGO_ALLOWED_HOSTS`. If no key is provided, a random one is generated into the git-ignored `.secret_key`
file. Never commit `.env`, `.secret_key` or `db.sqlite3`.

## Notes

- Sample product images are generated illustrations created by `seed_data`. Upload real photos from the dashboard
  (Products → Edit) at any time.
- Payment method is **Cash on delivery**; no online payment gateway is included.
