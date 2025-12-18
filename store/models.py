# Assuming file content starts with necessary imports and class declarations
# Truncated content for demonstration
... # Other lines of code

def calculate_total(quantity, item_price):
    total = Decimal(quantity) * Decimal(item_price)
    return total.quantize(Decimal('0.01'))
... # Other lines of code