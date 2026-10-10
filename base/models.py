from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

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
    is_veg = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu_images/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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