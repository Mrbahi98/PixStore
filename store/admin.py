from django.contrib import admin
from .models import Product
from .models import PaymentProof

admin.site.register(Product)

@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_method', 'uploaded_at')
    list_filter = ('payment_method', 'uploaded_at')
    search_fields = ('user__username',)
