# store/middleware.py
from django.utils.deprecation import MiddlewareMixin

class DisableCSRFForAdminAndCart(MiddlewareMixin):
    """
    Temporarily bypass CSRF checks for admin login and cart POST requests
    on Railway, where HTTPS proxy causes token mismatch.
    """
    def process_request(self, request):
        # Only disable CSRF for these paths
        if request.path.startswith('/admin/') or request.path.startswith('/cart/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
