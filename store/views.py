from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Product, Order, OrderItem
from django.conf import settings
from .store_utils import get_cart_count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext as _
from django.contrib import messages


message = _("Your payment has been received successfully.")

def home(request):
    products = Product.objects.all()
    return render(request, 'store/home.html', {'products': products})
# -------------------------------
# Helper function
# -------------------------------
# store/store_utils.py

def get_cart_count(request):
        cart = request.session.get('cart', {})
        return sum(cart.values())

# -------------------------------
# Page Views
# -------------------------------

def products_view(request):
    products = Product.objects.all()
    return render(request, 'store/products.html', {'products': products})

def about(request):
    return render(request, 'store/about.html')

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_details.html', {'product': product})

def cart_view(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(pk__in=cart.keys())

    cart_items = []
    total_price = 0

    for product in products:
        qty = cart[str(product.pk)]
        item_total = product.price * qty
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': qty,
            'item_total': item_total,
        })

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')

        if product_id and action:
            product_id = str(product_id)
            if action == 'increase':
                cart[product_id] = cart.get(product_id, 0) + 1
            elif action == 'decrease':
                if cart.get(product_id, 0) > 1:
                    cart[product_id] -= 1
                else:
                    cart.pop(product_id, None)
            elif action == 'remove':
                cart.pop(product_id, None)

            request.session['cart'] = cart
            request.session.modified = True
            return redirect('cart')

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': get_cart_count(request)
    })

@csrf_exempt
def update_cart_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        action = data.get('action')

        cart = request.session.get('cart', {})

        if action == 'increase':
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        elif action == 'decrease':
            if str(product_id) in cart:
                if cart[str(product_id)] > 1:
                    cart[str(product_id)] -= 1
                else:
                    del cart[str(product_id)]
        elif action == 'remove':
            cart.pop(str(product_id), None)

        request.session['cart'] = cart

        # Recalculate total
        from .models import Product
        total = 0
        for pid, qty in cart.items():
            try:
                product = Product.objects.get(pk=pid)
                total += product.price * qty
            except Product.DoesNotExist:
                pass

        return JsonResponse({'success': True, 'cart_count': sum(cart.values()), 'total': total})
    return JsonResponse({'success': False})

# -------------------------------
# Cart Actions
# -------------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from store.models import Product  # adjust import if your model path differs

# -------------------------------
# ADD TO CART
# -------------------------------
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True

    # redirect back to previous page or products page with ?added=1
    next_url = request.GET.get('next', reverse('products'))
    return redirect(f"{next_url}?added=1")


# -------------------------------
# REMOVE FROM CART
# -------------------------------
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')


# -------------------------------
# VIEW CART PAGE
# -------------------------------
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        item_total = product.price * quantity
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'item_total': item_total
        })

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })
# -------------------------------
# Orders Page
# -------------------------------
def my_orders(request):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).prefetch_related('orderitem_set')
    else:
        orders = []
# -------------------------------
# checkout summary page
# -------------------------------
def checkout_summary(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(pk__in=cart.keys())
    cart_items = []
    total_price = 0

    for product in products:
        qty = cart[str(product.pk)]
        item_total = product.price * qty
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': qty,
            'item_total': item_total,
        })

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        payment_method = request.POST.get('payment_method')

        # Save order in DB (example)
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            total_price=total_price,
            paid=False
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price
            )

        # Save basic checkout info in session
        request.session['checkout_data'] = {
            'name': name,
            'email': email,
            'payment_method': payment_method,
            'order_id': order.id,
            'total_price': total_price,
        }

        request.session['cart'] = {}  # empty cart after order

        # redirect to proof upload page
        return redirect('upload_payment_proof')

    return render(request, 'store/checkout_summary.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': get_cart_count(request)
    })

def checkout_success(request):
    return render(request, 'store/checkout_success.html', {
        'cart_count': get_cart_count(request)
    })

def checkout_summary(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(pk__in=cart.keys())
    cart_items = []
    total_price = 0

    for product in products:
        qty = cart[str(product.pk)]
        item_total = product.price * qty
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': qty,
            'item_total': item_total,
        })

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        payment_method = request.POST.get('payment_method')

        # Save order in DB (optional, keep if needed)
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            total_price=total_price,
            paid=False
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price
            )

        # Empty cart
        request.session['cart'] = {}

        # Redirect to proof upload page with selected payment method
        return redirect(f"/upload-payment-proof/?payment_method={payment_method}")

    return render(request, 'store/checkout_summary.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': get_cart_count(request)
    })

# payment proof
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import PaymentProof, Order
from .utils import get_cart_count  # adjust if your helper is elsewhere

def upload_payment_proof(request):
    payment_method = request.GET.get('payment_method', '')

    # Define your available accounts
    accounts = []
    if payment_method == "baridimob":
        accounts = [
            {"name": "الحساب الاول", "number": "00799999002063131521"},
            {"name": "الحساب الثاني", "number": "00799999002449551779"},
        ]
    elif payment_method == "crypto":
        accounts = [
            {"name": "Binance ID", "address": "461851594"},
            {"name": "Redotpay ID", "address": "1467680944"},
            {"name": "USDT BSC (BEP20)", "address": "0x97a8bf22824ab18eb92a391275ff51b98c1bd2ca"},
        ]

    # Handle proof upload
    if request.method == 'POST' and request.FILES.get('proof'):
        proof = request.FILES['proof']

        # Save proof to last order
        order = Order.objects.filter(user=request.user).last()
        if order:
            order.payment_proof = proof
            order.save()

        # Save proof separately in PaymentProof model
        PaymentProof.objects.create(
            user=request.user if request.user.is_authenticated else None,
            payment_method=payment_method,
            screenshot=proof
        )

        messages.success(request, "✅ Payment proof uploaded successfully.")
        return redirect('checkout_success')

    # Render upload page if not POST
    return render(request, 'store/upload_payment_proof.html', {
        'payment_method': payment_method,
        'accounts': accounts,
        'cart_count': get_cart_count(request),
    })
    return render(request, 'store/upload_payment_proof.html', context)
