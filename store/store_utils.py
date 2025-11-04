# store/store_utils.py

def get_cart_count(request):
    """
    Returns the total item count in the session cart.
    """
    cart = request.session.get('cart', {}) or {}
    return sum(int(q) for q in cart.values())
