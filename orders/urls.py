from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('', views.order_history, name='history'),
    path('<str:order_id>/confirmation/', views.confirmation, name='confirmation'),
    path('<str:order_id>/cancel/', views.cancel_order, name='cancel'),
    path('<str:order_id>/', views.order_detail, name='detail'),
]
