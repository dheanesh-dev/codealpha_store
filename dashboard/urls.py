from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),
    path('customers/', views.customer_list, name='customer_list'),
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/<int:pk>/update/', views.inventory_update, name='inventory_update'),
]
