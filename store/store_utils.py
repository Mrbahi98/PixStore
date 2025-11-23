# store/store_utils.py

def get_cart_count(request):
    """
    Returns the total item count in the session cart.
    """
    cart = request.session.get('cart', {}) or {}
    return sum(int(q) for q in cart.values())

from django.conf import settings

def to_usd(dzd):
    try:
        return round(float(dzd) / settings.DZD_PER_USD, 2)
    except:
        return 0.0
