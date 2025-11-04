def get_cart_count(request):
    cart = request.session.get('cart', {})
    return sum(cart.values())
