from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Product, Order, OrderItem, PaymentProof
from django.conf import settings
from .store_utils import get_cart_count
from django.http import JsonResponse
import json
from django.contrib import messages
from django.core.mail import send_mail
from decimal import Decimal

# -------------------------------
# Basic Pages
# -------------------------------
def home(request):
    products = Product.objects.all()
    return render(request, 'store/home.html', {'products': products})

def products_view(request):
    products = Product.objects.all()
    return render(request, 'store/products.html', {'products': products})

def about(request):
    return render(request, 'store/about.html')

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_details.html', {'product': product})


# -------------------------------
# CART SYSTEM
# -------------------------------
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True

    next_url = request.GET.get('next', reverse('products'))
    return redirect(f"{next_url}?added=1")


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    if product_id in cart:
        del cart[product_id]
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')


# ✅ ADDED MISSING FUNCTION TO MATCH URLS.PY
def update_cart_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            action = data.get('action')
            
            cart = request.session.get('cart', {})

            if product_id in cart:
                if action == 'increase':
                    cart[product_id] += 1
                elif action == 'decrease':
                    cart[product_id] -= 1
                    if cart[product_id] < 1:
                        del cart[product_id]
                elif action == 'remove':
                    del cart[product_id]

            request.session['cart'] = cart
            request.session.modified = True
            
            # Return success and new count for frontend JS to update
            return JsonResponse({'status': 'success', 'cart_count': sum(cart.values())})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def cart_view(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(pk__in=cart.keys())
    cart_items = []
    total_price = Decimal('0.00')

    for product in products:
        qty = cart[str(product.pk)]
        item_total = product.price * qty
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': qty,
            'item_total': item_total
        })

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': get_cart_count(request)
    })


# -------------------------------
# ORDERS
# -------------------------------
def my_orders(request):
    if request.user.is_authenticated:
        # Ensure 'items' matches the related_name in your OrderItem model
        orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
    else:
        orders = []
    return render(request, 'store/my_orders.html', {'orders': orders})


# -------------------------------
# CHECKOUT SUMMARY
# -------------------------------
def checkout_summary(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.info(request, "Your cart is empty.")
        return redirect('products')

    products = Product.objects.filter(pk__in=cart.keys())
    cart_items = []
    total_price = Decimal('0.00')

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

        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=name,
            email=email,
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

        # Save order ID for the next step
        request.session['last_order_id'] = order.id
        # Do NOT clear cart here. Wait for proof upload.

        return redirect(f"{reverse('upload_payment_proof')}?payment_method={payment_method}")

    return render(request, 'store/checkout_summary.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': get_cart_count(request)
    })


def checkout_success(request):
    return render(request, 'store/checkout_success.html', {
        'cart_count': get_cart_count(request)
    })


# -------------------------------
# UPLOAD PAYMENT PROOF
# -------------------------------
def upload_payment_proof(request):
    payment_method = request.GET.get('payment_method', '')

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

    if request.method == 'POST' and request.FILES.get('proof'):
        proof = request.FILES['proof']

        # Get the order
        order = None
        order_id = request.session.get('last_order_id')
        if order_id:
            order = Order.objects.filter(id=order_id).first()

        # Fallback for authenticated users if session was lost
        if not order and request.user.is_authenticated:
             order = Order.objects.filter(user=request.user).order_by('-created_at').first()

        if order:
            PaymentProof.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=order.name,
                email=order.email,
                payment_method=payment_method,
                screenshot=proof
            )

            # Send notification email
            send_mail(
                subject=f"New Payment Proof Uploaded - Order #{order.id}",
                message=(
                    f"A new payment proof has been uploaded.\n\n"
                    f"Order ID: {order.id}\n"
                    f"Name: {order.name or 'Guest'}\n"
                    f"Email: {order.email or 'Unknown'}\n"
                    f"Payment Method: {payment_method}\n"
                    f"Total Price: {order.total_price}\n"
                    f"---\n"
                    f"Please review it in the Django admin panel."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )

            # Clear cart and session data only after successful upload
            request.session['cart'] = {}
            if 'last_order_id' in request.session:
                del request.session['last_order_id']
            request.session.modified = True

            messages.success(request, "✅ Payment proof uploaded successfully.")
            return redirect('checkout_success')
        else:
            messages.error(request, "❌ Could not find your order. Please try placing it again.")
            return redirect('cart')

    return render(request, 'store/upload_payment_proof.html', {
        'payment_method': payment_method,
        'accounts': accounts,
        'cart_count': get_cart_count(request),
    })


