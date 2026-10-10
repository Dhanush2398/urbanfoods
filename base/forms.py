import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from .models import RestaurantProfile, MenuItem, CATEGORY_CHOICES,DeliveryPartnerProfile

User = get_user_model()


def normalize_phone(value):
    """Keep digits only; drop a leading +91 / 91 / 0 so '+91 98765 43210' == '9876543210'."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    username = forms.CharField(label="Phone number", max_length=20)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")

    def clean_username(self):
        phone = normalize_phone(self.cleaned_data["username"])
        if not re.fullmatch(r"[6-9]\d{9}", phone):
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(label="Phone number", max_length=20)
    remember = forms.BooleanField(required=False)

    def clean_username(self):
        return normalize_phone(self.cleaned_data["username"])


class RestaurantRegistrationForm(RegistrationForm):
    restaurant_name = forms.CharField(max_length=150)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
    city = forms.CharField(max_length=80)

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)
        RestaurantProfile.objects.create(
            user=user,
            restaurant_name=self.cleaned_data["restaurant_name"],
            address=self.cleaned_data["address"],
            city=self.cleaned_data["city"],
        )
        return user


class RestaurantDocumentForm(forms.ModelForm):
    class Meta:
        model = RestaurantProfile
        fields = ["image", "fssai_number", "fssai_certificate", "pan_number", "pan_card",
                  "gst_number", "gst_certificate", "latitude", "longitude"]

        widgets = {
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("image", "fssai_number", "fssai_certificate", "pan_number", "pan_card"):
            self.fields[name].required = True
        for f in self.fields.values():
            f.widget.attrs["class"] = "form-control"
        self.fields["image"].widget.attrs["accept"] = "image/*"

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if not img:
            raise forms.ValidationError("Restaurant image is required.")
        if hasattr(img, "size") and img.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Image must be under 2 MB.")
        return img

    def clean_pan_number(self):
        pan = self.cleaned_data["pan_number"].upper().strip()
        if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan):
            raise forms.ValidationError("Enter a valid PAN (e.g. ABCDE1234F).")
        return pan


class RestaurantLoginForm(PhoneLoginForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        profile = getattr(user, "restaurant", None)
        if profile is None:
            raise forms.ValidationError("This is not a restaurant account.", code="invalid_login")
        if profile.status != RestaurantProfile.APPROVED:
            raise forms.ValidationError("Your restaurant is not approved yet.", code="inactive")


class MenuItemForm(forms.ModelForm):
    categories = forms.MultipleChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Select at least one category."},
    )

    field_order = ["name", "categories", "price", "description", "image", "is_veg", "is_available"]

    class Meta:
        model = MenuItem
        fields = ["name", "price", "description", "image", "is_veg", "is_available"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["categories"] = self.instance.category_list
        for name, f in self.fields.items():
            if name == "categories":
                continue
            f.widget.attrs["class"] = (
                "form-check-input" if isinstance(f.widget, forms.CheckboxInput) else "form-control"
            )
        self.fields["image"].widget.attrs["accept"] = "image/*"

    def save(self, commit=True):
        item = super().save(commit=False)
        item.category_names = ",".join(self.cleaned_data["categories"])
        if commit:
            item.save()
        return item

class DeliveryRegistrationForm(RegistrationForm):
    city = forms.CharField(max_length=80)
    vehicle_type = forms.ChoiceField(choices=DeliveryPartnerProfile.VEHICLE_CHOICES)

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)
        DeliveryPartnerProfile.objects.create(
            user=user,
            city=self.cleaned_data["city"],
            vehicle_type=self.cleaned_data["vehicle_type"],
        )
        return user


class DeliveryDocumentForm(forms.ModelForm):
    class Meta:
        model = DeliveryPartnerProfile
        fields = ["photo", "driving_license_number", "driving_license", "vehicle_number", "rc_book"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("photo", "driving_license_number", "driving_license", "vehicle_number"):
            self.fields[name].required = True
        for f in self.fields.values():
            f.widget.attrs["class"] = "form-control"
        self.fields["photo"].widget.attrs["accept"] = "image/*"

    def clean_photo(self):
        img = self.cleaned_data.get("photo")
        if hasattr(img, "size") and img.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Photo must be under 2 MB.")
        return img

    def clean_vehicle_number(self):
        v = re.sub(r"[\s-]", "", self.cleaned_data["vehicle_number"]).upper()
        if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}", v):
            raise forms.ValidationError("Enter a valid vehicle number (e.g. KA01AB1234).")
        return v

    def clean_driving_license_number(self):
        return self.cleaned_data["driving_license_number"].strip().upper()


class DeliveryLoginForm(PhoneLoginForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if getattr(user, "delivery_partner", None) is None:
            raise forms.ValidationError("This is not a delivery partner account.", code="invalid_login")