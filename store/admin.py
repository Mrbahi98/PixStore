from django.contrib import admin
from .models import Product
from .models import PaymentProof
from django.utils.html import format_html

admin.site.register(Product)

@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'user', 'payment_method', 'uploaded_at', 'preview_image')
    readonly_fields = ('uploaded_at',)

    def preview_image(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="80" style="border-radius:8px;" />', obj.screenshot.url)
        return "No Image"
    preview_image.short_description = "Proof"

    search_fields = ('name', 'email', 'payment_method')
    list_filter = ('payment_method',)
