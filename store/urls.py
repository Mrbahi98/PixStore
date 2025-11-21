from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # homepage
    path('products/', views.products_view, name='products'),  # products page
    path('about/', views.about, name='about'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout-summary/', views.checkout_summary, name='checkout_summary'),
    path('upload-payment-proof/', views.upload_payment_proof, name='upload_payment_proof'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('orders/', views.my_orders, name='my_orders'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'), 
    path('contact/', views.contact, name='contact'),
]



