from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

CATEGORY_CHOICES = [
    ("Breakfast", "Breakfast"),
    ("Lunch", "Lunch"),
    ("Dinner", "Dinner"),
    ("Snacks", "Snacks"),
    ("Starters", "Starters"),
    ("Main Course", "Main Course"),
    ("Desserts", "Desserts"),
    ("Drinks", "Drinks"),
    ("Healthy", "Healthy"),
    ("South Indian", "South Indian"),
    ("North Indian", "North Indian"),
    ("Biryani", "Biryani"),
    ("Chinese", "Chinese"),
    ("Fast Food", "Fast Food"),
]


class RestaurantProfile(models.Model):
    INCOMPLETE, PENDING, APPROVED, REJECTED = "incomplete", "pending", "approved", "rejected"
    STATUS_CHOICES = [
        (INCOMPLETE, "Documents pending"),
        (PENDING, "Awaiting approval"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="restaurant")
    restaurant_name = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=80)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    image = models.ImageField(upload_to="restaurant_images/", blank=True)

    fssai_number = models.CharField(max_length=20, blank=True)
    fssai_certificate = models.FileField(upload_to="restaurant_docs/fssai/", blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    pan_card = models.FileField(upload_to="restaurant_docs/pan/", blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    gst_certificate = models.FileField(upload_to="restaurant_docs/gst/", blank=True)
    latitude = models.DecimalField(max_digits=10,decimal_places=7,null=True,blank=True)
    longitude = models.DecimalField(max_digits=10,decimal_places=7,null=True,blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=INCOMPLETE)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.restaurant_name


class MenuItem(models.Model):
    restaurant = models.ForeignKey(RestaurantProfile, on_delete=models.CASCADE, related_name="menu_items")
    name = models.CharField(max_length=120)
    category_names = models.CharField(max_length=300, blank=True)  # stored as "Breakfast,Healthy"
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    SERVING_UNIT_CHOICES = [
        ("Plate", "Plate"),
        ("Serving", "Serving"),
        ("Piece", "Piece"),
        ("Bowl", "Bowl"),
        ("Box", "Box"),
        ("Combo", "Combo"),
    ]
    serving_unit = models.CharField(max_length=20, choices=SERVING_UNIT_CHOICES, default="Serving")
    pieces_per_serving = models.PositiveIntegerField(null=True, blank=True, help_text="E.g., 6 (for 6 pieces in a plate)")
    quantity_in_grams_or_ml = models.PositiveIntegerField(null=True, blank=True, help_text="Weight or volume in grams/ml (e.g., 300 for 300g)")
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu_images/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Tax fields
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="CGST percentage (e.g. 2.5)")
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="SGST percentage (e.g. 2.5)")
    tax_inclusive = models.BooleanField(default=False, help_text="If true, the entered price includes GST.")


    class Meta:
        ordering = ["name"]

    @property
    def category_list(self):
        return [c for c in self.category_names.split(",") if c]

    def __str__(self):
        return f"{self.name} ({self.restaurant})"

class DeliveryPartnerProfile(models.Model):
    INCOMPLETE, PENDING, APPROVED, REJECTED = "incomplete", "pending", "approved", "rejected"
    STATUS_CHOICES = RestaurantProfile.STATUS_CHOICES
    VEHICLE_CHOICES = [("bike", "Motorbike"), ("scooter", "Scooter"), ("bicycle", "Bicycle")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="delivery_partner")
    city = models.CharField(max_length=80)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES, default="bike")
    photo = models.ImageField(upload_to="delivery/photos/", blank=True)
    driving_license_number = models.CharField(max_length=20, blank=True)
    driving_license = models.FileField(upload_to="delivery/license/", blank=True)
    vehicle_number = models.CharField(max_length=15, blank=True)
    rc_book = models.FileField(upload_to="delivery/rc/", blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=INCOMPLETE)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class CustomerAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    house_flat_no = models.CharField(max_length=100)
    street_area = models.CharField(max_length=200)
    landmark = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=20)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.is_default:
            CustomerAddress.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.house_flat_no}, {self.street_area}, {self.city}"

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    restaurant = models.ForeignKey(RestaurantProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_amount(self):
        from decimal import Decimal
        return sum((item.total_price for item in self.items.all()), Decimal('0.00'))

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    @property
    def base_price(self):
        return self.menu_item.price * self.quantity
        
    @property
    def taxable_value(self):
        from decimal import Decimal
        if self.menu_item.tax_inclusive:
            tax_rate = (self.menu_item.cgst_rate + self.menu_item.sgst_rate) / Decimal('100.00')
            val = self.base_price / (Decimal('1.00') + tax_rate)
            return val.quantize(Decimal('0.01'))
        return self.base_price.quantize(Decimal('0.01'))
        
    @property
    def cgst_amount(self):
        from decimal import Decimal
        return (self.taxable_value * (self.menu_item.cgst_rate / Decimal('100.00'))).quantize(Decimal('0.01'))
        
    @property
    def sgst_amount(self):
        from decimal import Decimal
        return (self.taxable_value * (self.menu_item.sgst_rate / Decimal('100.00'))).quantize(Decimal('0.01'))
        
    @property
    def item_total(self):
        return self.taxable_value + self.cgst_amount + self.sgst_amount
        
    @property
    def total_price(self):
        return self.item_total

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid (New)"),
        ("accepted", "Accepted"),
        ("preparing", "Preparing"),
        ("ready", "Ready for Pickup"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    restaurant = models.ForeignKey(RestaurantProfile, on_delete=models.SET_NULL, null=True)
    delivery_partner = models.ForeignKey(DeliveryPartnerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_orders")
    delivery_address = models.ForeignKey(CustomerAddress, on_delete=models.SET_NULL, null=True, related_name="+")
    delivery_address_text = models.TextField() 
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Advanced Tax Fields
    taxable_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cgst = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_sgst = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    wallet_applied = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_reference_id = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def process_payment_success(self):
        from django.db import transaction
        with transaction.atomic():
            if hasattr(self, 'ledger_entries') and self.ledger_entries.filter(transaction_type='order_payment').exists():
                return
            
            commission_rate = Decimal('10.00')
            commission_amount = (self.subtotal * (commission_rate / Decimal('100.00'))).quantize(Decimal('0.01'))
            restaurant_net = self.subtotal - commission_amount + self.gst
            
            LedgerEntry.objects.create(
                reference=f"PAY_{self.transaction_id}",
                order=self,
                amount=self.total_amount,
                currency="INR",
                eligible_food_subtotal=self.subtotal,
                platform_commission_rate=commission_rate,
                platform_commission=commission_amount,
                restaurant_earnings=restaurant_net,
                delivery_fee=self.delivery_fee,
                taxes=self.gst,
                discounts=Decimal('0.00'),
                transaction_type="order_payment",
                direction="credit",
                status="completed"
            )
            
            if self.restaurant:
                earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=self.restaurant)
                earnings.total_eligible_sales += self.subtotal
                earnings.total_commission_deducted += commission_amount
                earnings.net_earnings += restaurant_net
                earnings.available_balance += restaurant_net
                earnings.save()

    def process_order_delivered(self):
        from django.db import transaction
        from django.utils import timezone
        with transaction.atomic():
            if self.status != 'delivered':
                return
            
            entry = self.ledger_entries.filter(transaction_type='order_payment').first()
            if entry and self.restaurant:
                earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=self.restaurant)
                
                if earnings.pending_balance >= entry.restaurant_earnings:
                    earnings.pending_balance -= entry.restaurant_earnings
                    earnings.available_balance += entry.restaurant_earnings
                    earnings.save()
                    
                entry.settled_at = timezone.now()
                entry.save()

    def process_refund(self):
        from django.db import transaction
        import uuid
        with transaction.atomic():
            payment_entry = self.ledger_entries.filter(transaction_type='order_payment').first()
            if not payment_entry:
                return
            
            if self.ledger_entries.filter(transaction_type='refund').exists():
                return
            
            ref_id = f"REF_{uuid.uuid4().hex[:12].upper()}"
            LedgerEntry.objects.create(
                reference=ref_id,
                order=self,
                amount=payment_entry.amount,
                currency="INR",
                eligible_food_subtotal=payment_entry.eligible_food_subtotal,
                platform_commission_rate=payment_entry.platform_commission_rate,
                platform_commission=payment_entry.platform_commission,
                restaurant_earnings=payment_entry.restaurant_earnings,
                delivery_fee=payment_entry.delivery_fee,
                taxes=payment_entry.taxes,
                discounts=Decimal('0.00'),
                transaction_type="refund",
                direction="debit",
                status="completed"
            )
            
            if self.restaurant:
                earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=self.restaurant)
                earnings.total_eligible_sales -= payment_entry.eligible_food_subtotal
                earnings.total_commission_deducted -= payment_entry.platform_commission
                earnings.net_earnings -= payment_entry.restaurant_earnings
                
                if payment_entry.settled_at:
                    earnings.available_balance -= payment_entry.restaurant_earnings
                else:
                    earnings.pending_balance -= payment_entry.restaurant_earnings
                
                earnings.save()

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    
    item_name = models.CharField(max_length=120)
    serving_unit = models.CharField(max_length=20)
    pieces_per_serving = models.PositiveIntegerField(null=True, blank=True)
    quantity_in_grams_or_ml = models.PositiveIntegerField(null=True, blank=True)
    
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Advanced Tax Snapshot
    taxable_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_inclusive = models.BooleanField(default=False)

    
    def __str__(self):
        return f"{self.quantity} x {self.item_name} for Order #{self.order.id}"

class CustomerWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)

class CustomerWalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("credit", "Credit"),
        ("debit", "Debit")
    ]
    wallet = models.ForeignKey(CustomerWallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class LedgerEntry(models.Model):
    TRANSACTION_TYPES = [
        ("order_payment", "Order Payment"),
        ("refund", "Refund"),
        ("reversal", "Reversal"),
        ("withdrawal", "Withdrawal"),
        ("promo", "Promo Credit"),
    ]
    
    reference = models.CharField(max_length=100, unique=True)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries")
    
    amount = models.DecimalField(max_digits=12, decimal_places=2) 
    currency = models.CharField(max_length=3, default="INR")
    
    eligible_food_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    platform_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    restaurant_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    taxes = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    discounts = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    direction = models.CharField(max_length=10, choices=[("credit", "Credit"), ("debit", "Debit")])
    status = models.CharField(max_length=20, default="completed") 
    
    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

class RestaurantEarnings(models.Model):
    restaurant = models.OneToOneField(RestaurantProfile, on_delete=models.CASCADE, related_name="earnings")
    total_eligible_sales = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_commission_deducted = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    pending_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    withdrawn_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    reserved_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    updated_at = models.DateTimeField(auto_now=True)

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
        ("failed", "Failed"),
    ]
    restaurant = models.ForeignKey(RestaurantProfile, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    destination_details = models.TextField(help_text="Bank account or UPI details")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    payout_reference = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Order #{self.order.id} status changed to {self.new_status}"

class DeliveryPartnerLocation(models.Model):
    partner = models.OneToOneField(DeliveryPartnerProfile, on_delete=models.CASCADE, related_name="location")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Location for {self.partner.user.username}"

class RestaurantPayoutSettings(models.Model):
    PAYOUT_METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('qr', 'QR Code'),
    ]
    restaurant = models.OneToOneField(RestaurantProfile, on_delete=models.CASCADE, related_name="payout_settings")
    payout_method = models.CharField(max_length=10, choices=PAYOUT_METHOD_CHOICES, default='bank')
    
    # Bank Details
    account_holder_name = models.CharField(max_length=150, blank=True, null=True)
    bank_name = models.CharField(max_length=150, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    
    # UPI Details
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    upi_account_holder_name = models.CharField(max_length=150, blank=True, null=True)
    
    # QR Code
    qr_code_image = models.ImageField(upload_to="payout_qrs/", blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def get_snapshot(self):
        if self.payout_method == 'bank':
            return f"Bank: {self.bank_name}, Acct: {self.account_number}, IFSC: {self.ifsc_code}, Holder: {self.account_holder_name}"
        elif self.payout_method == 'upi':
            return f"UPI ID: {self.upi_id}, Holder: {self.upi_account_holder_name}"
        elif self.payout_method == 'qr':
            return f"QR Code Image: {self.qr_code_image.url if self.qr_code_image else 'Not provided'}"
        return "Not set"
