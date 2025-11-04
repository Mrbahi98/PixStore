from .utils import get_cart_count

def cart_count_context(request):
    return {'cart_count': get_cart_count(request)}
def cart_count(request):
    return {'cart_count': get_cart_count(request)}
