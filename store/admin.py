from django.contrib import admin
from .models import Product, Order
from .models import PaymentProof
from django.utils.html import format_html

admin.site.register(Product)
@admin.register(PaymentProof)
@admin.register(Order)

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

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'id')

    actions = ['mark_as_review', 'mark_as_confirmed', 'mark_as_sent']

    def mark_as_review(self, request, queryset):
        queryset.update(status='review')
    mark_as_review.short_description = "Mark as Payment Under Review"

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
    mark_as_confirmed.short_description = "Mark as Payment Confirmed"

    def mark_as_sent(self, request, queryset):
        queryset.update(status='sent')
    mark_as_sent.short_description = "Mark as Products Delivered"
