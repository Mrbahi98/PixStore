from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Product, Order, OrderItem, PaymentProof
from django.conf import settings
from .store_utils import get_cart_count
from django.http import JsonResponse
import json
from django.contrib import messages
from django.core.mail import send_mail
from decimal import Decimal
from anymail.message import AnymailMessage
from django.template.loader import render_to_string
import threading
import logging

logger = logging.getLogger(__name__)

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


def remove_from_cart(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id = str(request.POST.get('product_id', ''))
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
from django.db.models import Prefetch

def my_orders(request):
    """
    Show orders for authenticated users, or allow guest email lookup.
    If user is not logged in, show a small form to enter an email to lookup orders.
    """
    orders = []
    lookup_email = None
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).order_by('-created_at')
    else:
        # If guest submitted an email to lookup orders (optional)
        if request.method == 'POST':
            lookup_email = request.POST.get('email', '').strip()
            if lookup_email:
                orders = Order.objects.filter(email__iexact=lookup_email).prefetch_related(
                    Prefetch('items', queryset=OrderItem.objects.select_related('product'))
                ).order_by('-created_at')

    return render(request, 'store/my_orders.html', {
        'orders': orders,
        'lookup_email': lookup_email,
        'cart_count': get_cart_count(request),
    })

# -------------------------------
# CHECKOUT SUMMARY
# -------------------------------
def _send_order_confirmation(order_id):
    try:
        o = Order.objects.get(pk=order_id)
        if not o.email:
            return

        from django.template.loader import render_to_string
        from anymail.message import AnymailMessage

        ctx = {
            "order": o,
            "name": o.name or "Customer",
            "site_url": "https://pixstore-production.up.railway.app"  # your real domain
        }

        # Render templates
        plain = render_to_string(
            "store/emails/order_confirmation.txt",
            ctx
        )
        html = render_to_string(
            "store/emails/order_confirmation.html",
            ctx
        )

        msg = AnymailMessage(
            subject=f"تأكيد الطلب — PixStore #{o.id}",
            body=plain,
            from_email="PixStore <itbobo8@googlemail.com>",
            to=[o.email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send()

    except Exception:
        logging.exception("Order confirmation send failed for order %s", order_id)


def checkout_summary(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.info(request, "Your cart is empty.")
        return redirect('products')

    # convert keys to ints to avoid DB mismatch
    try:
        cart_product_ids = [int(k) for k in cart.keys()]
    except Exception:
        cart_product_ids = list(cart.keys())

    products = Product.objects.filter(pk__in=cart_product_ids)
    cart_items = []
    total_price = Decimal('0.00')

    for product in products:
        qty = cart.get(str(product.pk), 0)
        item_total = product.price * qty
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': qty,
            'item_total': item_total,
        })

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        payment_method = request.POST.get('payment_method', '').strip()

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
# Paste/replace this whole function in store/views.py
import threading
import logging

logger = logging.getLogger(__name__)

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

    # Local uploaded logo path for testing (will be transformed to public URL by your platform)
    # For production replace with your static absolute URL:
    # "https://pixstore-production.up.railway.app/static/images/pixstore-logo-v2.png"
    logo_url = "/mnt/data/Screenshot 2025-11-23 213945.png"

    if request.method == 'POST' and request.FILES.get('proof'):
        proof = request.FILES['proof']

        # Get the order from session
        order = None
        order_id = request.session.get('last_order_id')
        if order_id:
            order = Order.objects.filter(id=order_id).first()

        # Fallback for authenticated users (in case session was lost)
        if not order and request.user.is_authenticated:
            order = Order.objects.filter(user=request.user).order_by('-created_at').first()

        if order:
            # Save the proof
            PaymentProof.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=order.name,
                email=order.email,
                payment_method=payment_method,
                screenshot=proof
            )

            # --- Prepare admin recipients robustly ---
            raw_admins = getattr(settings, "ADMIN_NOTIFICATION_EMAILS", None)
            if isinstance(raw_admins, str):
                recipient_list = [e.strip() for e in raw_admins.split(",") if e.strip()]
            elif isinstance(raw_admins, (list, tuple)):
                recipient_list = [e.strip() for e in raw_admins if e and e.strip()]
            else:
                recipient_list = [settings.DEFAULT_FROM_EMAIL]

            # Ensure at least one recipient and dedupe
            if not recipient_list:
                recipient_list = [settings.DEFAULT_FROM_EMAIL]
            seen = set()
            clean_recipients = []
            for r in recipient_list:
                low = r.lower()
                if low not in seen:
                    clean_recipients.append(r)
                    seen.add(low)
            recipient_list = clean_recipients

            # --- Send admin notification, log everything ---
            try:
                logger.info("Sending admin payment proof notification for order %s to %s", order.id, recipient_list)
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
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
                logger.info("Admin notification sent for order %s", order.id)

                # --- Only after admin notify succeeded, start customer confirmation ---
                try:
                    threading.Thread(target=_send_order_confirmation, args=(order.id,), daemon=True).start()
                    logger.info("Started customer confirmation thread for order %s", order.id)
                except Exception:
                    logger.exception("Failed to start customer confirmation thread for order %s", order.id)

            except Exception as e:
                # Log the real error so you can inspect Railway logs & Brevo failure
                logger.exception("Admin notification failed for order %s: %s", order.id, e)
                # Optionally inform admin via UI; we continue to clear session or not depending on policy
                messages.error(request, "❌ Failed to send admin notification — please check logs.")
                # You may want to *not* clear session/cart in this case so you can retry
                return redirect('cart')

            # Clear cart and session data only after successful upload & admin notification
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
        'logo_url': logo_url,  # optional: use in your template to preview the logo
    })

#Contact us
def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')

        # Compose admin notification email
        subject = f"📩 New Contact Message from {name}"
        admin_message_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color:#f7f7f7; padding:20px;">
            <div style="background:white; border-radius:8px; padding:20px; max-width:600px; margin:auto;">
              <h2 style="color:#009ffd;">New Contact Message</h2>
              <p><strong>Name:</strong> {name}</p>
              <p><strong>Email:</strong> {email}</p>
              <p><strong>Message:</strong><br>{message_text.replace('\n','<br>')}</p>
              <hr style="margin:20px 0;">
              <p style="font-size:13px;color:#777;">Sent from PixStore Contact Page</p>
            </div>
          </body>
        </html>
        """

        try:
            # Send to admin (you)
            admin_msg = AnymailMessage(
                subject=subject,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_FROM_EMAIL],
                reply_to=[email],
            )
            admin_msg.attach_alternative(admin_message_html, "text/html")
            admin_msg.send()

            # Send confirmation email to user
            confirm_subject = "✅ Thanks for contacting PixStore!"
            confirm_html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">
                <div style="background:white; border-radius:8px; padding:20px; max-width:600px; margin:auto;">
                  <h2 style="color:#009ffd;">Hey {name},</h2>
                  <p>Thanks for reaching out to <strong>PixStore</strong>! We’ve received your message and will get back to you soon.</p>
                  <p><strong>Your message:</strong></p>
                  <blockquote style="color:#555;">{message_text.replace('\n','<br>')}</blockquote>
                  <hr style="margin:20px 0;">
                  <p style="font-size:13px;color:#777;">This is an automated confirmation from PixStore.</p>
                </div>
              </body>
            </html>
            """
            confirm_msg = AnymailMessage(
                subject=confirm_subject,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            confirm_msg.attach_alternative(confirm_html, "text/html")
            confirm_msg.send()

            success = True
        except Exception as e:
            print("Error sending email via Brevo:", e)
            success = False

        return render(request, 'store/contact.html', {'success': success})

    return render(request, 'store/contact.html')
