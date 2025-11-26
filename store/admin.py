from django.contrib import admin
from .models import Product, Order, OrderItem, PaymentProof
from django.utils.html import format_html

admin.site.register(Product)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "total_price", "status", "paid", "created_at")
    list_filter = ("status", "paid", "created_at")
    search_fields = ("id", "name", "email")
    inlines = [OrderItemInline]

@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    # These fields MUST exist on PaymentProof model
    list_display = ("id", "name", "email", "payment_method")
    search_fields = ("name", "email", "payment_method")
    # keep it simple for now; no readonly_fields, no list_filter
    pass
