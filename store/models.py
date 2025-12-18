# Assuming file content starts with necessary imports and class declarations
# Truncated content for demonstration
... # Other lines of code

<<<<<<< HEAD
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

from cloudinary.models import CloudinaryField

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    old_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    image = CloudinaryField('image', folder='products/')
    file = models.FileField(upload_to='products/', null=True, blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )

    created_at = models.DateTimeField(auto_now_add=True)
   
    def __str__(self):
        return self.name
    
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0

# ------------------------------
# ORDER MODEL
# ------------------------------
from django.contrib.auth import get_user_model

User = get_user_model()

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending — awaiting payment'),
        ('review', 'Payment under review'),
        ('confirmed', 'Payment confirmed'),
        ('sent', 'Products delivered'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    paid = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        display_name = self.name or (self.user.username if self.user else "Guest")
        return f"Order #{self.id or 'unsaved'} - {display_name}"

    def save(self, *args, **kwargs):
        """
        🔐 SINGLE SOURCE OF TRUTH:
        If status becomes 'confirmed', the order is paid.
        """
        if self.status == 'confirmed' and not self.paid:
            self.paid = True
        super().save(*args, **kwargs)

    def get_total_price(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += (item.price or Decimal('0.00')) * item.quantity
        return total.quantize(Decimal('0.01'))

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
=======
def calculate_total(quantity, item_price):
    total = Decimal(quantity) * Decimal(item_price)
    return total.quantize(Decimal('0.01'))
... # Other lines of code
>>>>>>> bd6ae11f8d0cc000af9a2c4d4e6a2c2cb6388274
