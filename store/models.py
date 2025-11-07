from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField


# ------------------------------
# CATEGORY MODEL
# ------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# ------------------------------
# PRODUCT MODEL
# ------------------------------
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    old_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    image = CloudinaryField('image', folder='products/')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.name

    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0


# ------------------------------
# ORDER MODEL
# ------------------------------
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        # Prefer name > username > Guest
        display_name = self.name or (self.user.username if self.user else "Guest")
        return f"Order #{self.id} - {display_name}"

    def get_total_price(self):
        # Compute from related items
        total = sum(item.price * item.quantity for item in self.orderitem_set.all())
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

# ------------------------------
# PAYMENT PROOF MODEL
# ------------------------------
class PaymentProof(models.Model):
    PAYMENT_METHODS = [
        ('baridimob', 'Baridimob'),
        ('crypto', 'Crypto'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    screenshot = CloudinaryField('image', folder='payment_proofs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or self.user or 'Guest'} - {self.payment_method}"
