import uuid
from django.db import models
from django.conf import settings
from .tenants import TenantProfile
from middleware.models import TenantIsolatedModel

class Category(TenantIsolatedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Product(TenantIsolatedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True, verbose_name="Product Code / SKU")
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Pharmacy-only fields
    batch_number = models.CharField(max_length=100, null=True, blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    nafdac_number = models.CharField(max_length=100, null=True, blank=True)

    # Provision store-only fields
    reorder_level = models.PositiveIntegerField(null=True, blank=True)
    supplier_code = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Sale(TenantIsolatedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='sales')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sales')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale {self.id} - {self.total_amount}"

    @property
    def has_returns(self):
        return self.returns.exists()

    @property
    def total_returned_amount(self):
        return sum((ret.return_subtotal for ret in self.returns.all()), 0)

    @property
    def total_exchange_amount(self):
        return sum((ret.exchange_subtotal for ret in self.returns.all()), 0)

    @property
    def total_refund_amount(self):
        return sum((ret.refund_amount for ret in self.returns.all()), 0)

    @property
    def total_additional_collected(self):
        return sum((ret.additional_amount for ret in self.returns.all()), 0)

    @property
    def net_total(self):
        return self.total_amount - self.total_refund_amount + self.total_additional_collected

    @property
    def status(self):
        if not self.returns.exists():
            return 'completed'
        items = self.items.all()
        if not items:
            return 'completed'
        all_returned = all(item.remaining_quantity == 0 for item in items)
        has_exchange = any(ret.exchange_items.exists() for ret in self.returns.all())
        if all_returned and not has_exchange:
            return 'returned'
        elif has_exchange:
            return 'exchanged'
        else:
            return 'partially_returned'

    @property
    def status_display(self):
        status_map = {
            'completed': 'Completed',
            'exchanged': 'Exchanged',
            'returned': 'Fully Returned / Refunded',
            'partially_returned': 'Partially Returned',
        }
        return status_map.get(self.status, 'Completed')

    @property
    def can_return(self):
        return any(item.can_return for item in self.items.all())


class SaleItem(TenantIsolatedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='sale_items')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sale_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def returned_quantity(self):
        return sum((ret_item.quantity for ret_item in self.returns.all()), 0)

    @property
    def remaining_quantity(self):
        return max(0, self.quantity - self.returned_quantity)

    @property
    def can_return(self):
        return self.remaining_quantity > 0

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def active_line_total(self):
        return self.unit_price * self.remaining_quantity


class ReturnTransaction(TenantIsolatedModel):
    RETURN_TYPE_CHOICES = [
        ('refund', 'Refund Only'),
        ('exchange', 'Product Exchange / Swap'),
        ('store_credit', 'Store Credit'),
    ]

    REASON_CHOICES = [
        ('damaged', 'Defective / Damaged'),
        ('wrong_item', 'Wrong Item / Size'),
        ('customer_request', 'Customer Changed Mind'),
        ('expired', 'Expired Product'),
        ('other', 'Other Reason'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='returns')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='processed_returns')
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES, default='refund')
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, default='customer_request')
    reason_details = models.TextField(blank=True)
    return_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    exchange_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    additional_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Return {self.id} for Sale {self.sale.id} ({self.get_return_type_display()})"


class ReturnItem(TenantIsolatedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='returned_items')
    return_transaction = models.ForeignKey(ReturnTransaction, on_delete=models.CASCADE, related_name='returned_items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='returns')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    restocked = models.BooleanField(default=True, verbose_name="Restocked into Inventory")

    def __str__(self):
        return f"Returned: {self.product.name} x {self.quantity}"

    @property
    def total_refund_value(self):
        return self.unit_price * self.quantity


class ExchangeItem(TenantIsolatedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='exchange_items')
    return_transaction = models.ForeignKey(ReturnTransaction, on_delete=models.CASCADE, related_name='exchange_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='exchanges')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Exchange Replacement: {self.product.name} x {self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

