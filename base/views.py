import datetime
from django.utils import timezone
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponse
from django.db import models
from django.db.models import Count, Q, Sum
from decimal import Decimal
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import json
import base64
import hashlib
import requests
import uuid
from django.conf import settings
from .forms import (
    DeliveryLoginForm, PhoneLoginForm, RegistrationForm, RestaurantRegistrationForm,
    RestaurantDocumentForm, RestaurantLoginForm, MenuItemForm, DeliveryRegistrationForm, DeliveryDocumentForm, DeliveryLoginForm,
    UserUpdateForm, CustomerAddressForm
)
from .models import OrderStatusHistory, DeliveryPartnerLocation
from .models import (
    RestaurantProfile, MenuItem, CATEGORY_CHOICES, DeliveryPartnerProfile, 
    CustomerAddress, Cart, CartItem, Order, OrderItem,
    LedgerEntry, WithdrawalRequest, RestaurantEarnings, CustomerWallet, RestaurantPayoutSettings
)
from django.core.paginator import Paginator
staff_only = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="base:login")

from django.db.models import Count, Q

def home(request):
    restaurants = RestaurantProfile.objects.filter(
        status=RestaurantProfile.APPROVED
    ).order_by("-created_at")

    breakfast_restaurants = (
        RestaurantProfile.objects
        .filter(status=RestaurantProfile.APPROVED)
        .annotate(breakfast_count=Count(
            "menu_items",
            filter=Q(menu_items__is_available=True,
                     menu_items__category_names__icontains="Breakfast"),
            distinct=True,
        ))
        .filter(breakfast_count__gt=0)
        .order_by("-created_at")[:8]
    )

    south_indian_restaurants = (
        RestaurantProfile.objects
        .filter(status=RestaurantProfile.APPROVED)
        .annotate(item_count=Count(
            "menu_items",
            filter=Q(menu_items__is_available=True,
                     menu_items__category_names__icontains="South Indian"),
            distinct=True,
        ))
        .filter(item_count__gt=0)
        .order_by("-created_at")[:12]
    )

    return render(request, "index.html", {
        "restaurants": restaurants,
        "breakfast_restaurants": breakfast_restaurants,
        "south_indian_restaurants": south_indian_restaurants,
    })

@login_required
def profile(request):
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("base:profile")
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, "profile.html", {"form": form})

@login_required
def manage_addresses(request):
    addresses = request.user.addresses.all()
    return render(request, "addresses.html", {"addresses": addresses})

@login_required
def add_address(request):
    if request.method == "POST":
        form = CustomerAddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            if not request.user.addresses.exists():
                addr.is_default = True
            addr.save()
            messages.success(request, "Address added successfully.")
            return redirect("base:manage_addresses")
    else:
        form = CustomerAddressForm(initial={"recipient_name": request.user.get_full_name(), "phone_number": request.user.username})
    return render(request, "address_form.html", {"form": form})

@login_required
def edit_address(request, pk):
    addr = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    if request.method == "POST":
        form = CustomerAddressForm(request.POST, instance=addr)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully.")
            return redirect("base:manage_addresses")
    else:
        form = CustomerAddressForm(instance=addr)
    return render(request, "address_form.html", {"form": form, "editing": True})

@login_required
@require_POST
def delete_address(request, pk):
    addr = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    addr.delete()
    messages.success(request, "Address deleted.")
    return redirect("base:manage_addresses")

@login_required
@require_POST
def set_default_address(request, pk):
    addr = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    addr.is_default = True
    addr.save()
    messages.success(request, "Default address updated.")
    return redirect("base:manage_addresses")


def authView(request):
    """Sign up."""
    if request.user.is_authenticated:
        return redirect("base:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration completed. Please sign in.")
            return redirect("base:login")
        messages.error(request, "Please correct the errors below")
    else:
        form = RegistrationForm()

    return render(request, "registration/signup.html", {"form": form})


class UrbanLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = PhoneLoginForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        if user.is_staff:
            return reverse("base:dashboard")
        elif hasattr(user, 'restaurant') and user.restaurant:
            return reverse("base:restaurant_dashboard")
        return super().get_success_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember"):
            self.request.session.set_expiry(0)
        return response


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("base:login")


def restaurant_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("base:restaurant_login")


# ---------- restaurant side ----------
def restaurant_required(view):
    @login_required(login_url="base:restaurant_login")
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "restaurant", None)
        if profile is None:
            messages.error(request, "This is not a restaurant account.")
            return redirect("base:restaurant_login")
        request.restaurant = profile
        return view(request, *args, **kwargs)
    return wrapper


def restaurant_signup(request):
    if request.user.is_authenticated:
        return redirect("base:restaurant_documents")
    if request.method == "POST":
        form = RestaurantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Account created. Please upload your documents.")
            return redirect("base:restaurant_documents")
        messages.error(request, "Please correct the errors below")
    else:
        form = RestaurantRegistrationForm()
    return render(request, "registration/restaurant_signup.html", {"form": form})


class RestaurantLoginView(LoginView):
    template_name = "registration/restaurant_login.html"
    authentication_form = RestaurantLoginForm
    redirect_authenticated_user = False

    def get_success_url(self):
        return reverse("base:restaurant_dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember"):
            self.request.session.set_expiry(0)
        return response


@restaurant_required
def restaurant_documents(request):
    profile = request.restaurant
    if profile.status == RestaurantProfile.APPROVED:
        return redirect("base:restaurant_dashboard")

    if profile.status == RestaurantProfile.PENDING:
        form = None
    elif request.method == "POST":
        form = RestaurantDocumentForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            p.status = RestaurantProfile.PENDING
            p.rejection_reason = ""
            p.submitted_at = timezone.now()
            p.save()
            messages.success(request, "Documents submitted. We'll notify you after verification.")
            return redirect("base:restaurant_documents")
    else:
        form = RestaurantDocumentForm(instance=profile)
    return render(request, "restaurant/documents.html", {"form": form, "profile": profile})


@restaurant_required
def restaurant_dashboard(request):
    if request.restaurant.status != RestaurantProfile.APPROVED:
        return redirect("base:restaurant_documents")
        
    orders = Order.objects.filter(restaurant=request.restaurant).exclude(payment_status='pending').order_by('-created_at')
    orders = orders.prefetch_related('items__menu_item', 'ledger_entries')
    
    from .models import RestaurantEarnings
    earnings = RestaurantEarnings.objects.filter(restaurant=request.restaurant).first()
    
    from django.utils import timezone
    today = timezone.now().date()
    
    today_revenue = sum([
        o.ledger_entries.filter(transaction_type='order_payment').first().restaurant_earnings 
        for o in orders.filter(created_at__date=today) 
        if o.ledger_entries.filter(transaction_type='order_payment').exists()
    ])
        
    return render(request, "restaurant/dashboard.html", {
        "profile": request.restaurant,
        "menu_count": request.restaurant.menu_items.count(),
        "orders": orders,
        "total_orders": orders.count(),
        "today_revenue": today_revenue,
        "earnings": earnings
    })

@login_required
@restaurant_required
@require_POST
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk, restaurant=request.restaurant)
    new_status = request.POST.get('status')
    
    valid_transitions = {
        'paid': ['accepted', 'rejected'],
        'accepted': ['preparing'],
        'preparing': ['ready'],
    }
    
    if new_status in valid_transitions.get(order.status, []):
        old_status = order.status
        order.status = new_status
        order.save()
        OrderStatusHistory.objects.create(order=order, previous_status=old_status, new_status=new_status, changed_by=request.user)
        messages.success(request, f"Order #{order.id} marked as {order.get_status_display()}.")
        if new_status == 'rejected':
            order.process_refund()
    else:
        messages.error(request, "Invalid status transition.")
        
    return redirect('base:restaurant_dashboard')


# ---------- admin side ----------
@staff_only
def dashboard(request):

    pending_count = RestaurantProfile.objects.filter(
        status=RestaurantProfile.PENDING
    ).count()

    total_restaurants = RestaurantProfile.objects.count()

    pending_delivery_count = DeliveryPartnerProfile.objects.filter(
        status=DeliveryPartnerProfile.PENDING
    ).count()

    total_delivery_partners = DeliveryPartnerProfile.objects.count()

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "pending_count": pending_count,
            "total_restaurants": total_restaurants,

            "pending_delivery_count": pending_delivery_count,
            "total_delivery_partners": total_delivery_partners,
        },
    )


@staff_only
def restaurant_requests(request):
    profiles = (RestaurantProfile.objects.select_related("user")
                .filter(status=RestaurantProfile.PENDING).order_by("-submitted_at"))
    return render(request, "dashboard/restaurant_requests.html", {"profiles": profiles})


@staff_only
def restaurant_list(request):
    status = request.GET.get("status", "")
    profiles = RestaurantProfile.objects.select_related("user").order_by("-created_at")
    if status in dict(RestaurantProfile.STATUS_CHOICES):
        profiles = profiles.filter(status=status)
    return render(request, "dashboard/restaurant_list.html", {
        "profiles": profiles,
        "status": status,
        "status_choices": RestaurantProfile.STATUS_CHOICES,
    })


@staff_only
@require_POST
def restaurant_review(request, pk):
    profile = get_object_or_404(RestaurantProfile, pk=pk, status=RestaurantProfile.PENDING)
    action = request.POST.get("action")
    if action == "approve":
        profile.status = RestaurantProfile.APPROVED
        profile.rejection_reason = ""
    elif action == "reject":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Give a reason for rejection.")
            return redirect("base:restaurant_requests")
        profile.status = RestaurantProfile.REJECTED
        profile.rejection_reason = reason
    else:
        return redirect("base:restaurant_requests")
    profile.reviewed_at = timezone.now()
    profile.reviewed_by = request.user
    profile.save()
    messages.success(request, f"{profile.restaurant_name}: {profile.get_status_display()}")
    return redirect("base:restaurant_requests")


@staff_only
def restaurant_detail(request, pk):
    profile = get_object_or_404(RestaurantProfile.objects.select_related("user", "reviewed_by"), pk=pk)
    return render(request, "dashboard/restaurant_detail.html", {"p": profile})

@restaurant_required
def restaurant_menu(request, pk=None):
    profile = request.restaurant
    if profile.status != RestaurantProfile.APPROVED:
        return redirect("base:restaurant_documents")

    instance = get_object_or_404(MenuItem, pk=pk, restaurant=profile) if pk else None

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            item = form.save(commit=False)
            item.restaurant = profile
            item.save()
            messages.success(request, "Menu item saved.")
            return redirect("base:restaurant_menu")
    else:
        form = MenuItemForm(instance=instance)

    return render(request, "restaurant/menu.html", {
        "form": form,
        "editing": instance,
        "items": profile.menu_items.all(),
    })


@restaurant_required
@require_POST
def restaurant_menu_delete(request, pk):
    item = get_object_or_404(MenuItem, pk=pk, restaurant=request.restaurant)
    item.delete()
    messages.success(request, "Menu item deleted.")
    return redirect("base:restaurant_menu")


def restaurant_public(request, pk):
    restaurant = get_object_or_404(RestaurantProfile, pk=pk, status=RestaurantProfile.APPROVED)
    items = restaurant.menu_items.filter(is_available=True)
    return render(request, "restaurant_public.html", {"r": restaurant, "items": items})


def menu_item_public(request, pk):
    item = get_object_or_404(
        MenuItem.objects.select_related("restaurant"),
        pk=pk,
        is_available=True,
        restaurant__status=RestaurantProfile.APPROVED,
    )
    return render(request, "menu_item_public.html", {"i": item, "r": item.restaurant})

def restaurant_category(request, pk, category):
    restaurant = get_object_or_404(RestaurantProfile, pk=pk, status=RestaurantProfile.APPROVED)
    if category not in dict(CATEGORY_CHOICES):
        raise Http404
    items = restaurant.menu_items.filter(
        is_available=True,
        category_names__icontains=category,
    )
    return render(request, "restaurant_category.html", {
        "r": restaurant,
        "items": items,
        "category": category,
    })



def restaurant_directory(request):
    q = request.GET.get("q", "").strip()
    selected = [c for c in request.GET.getlist("cuisine") if c in dict(CATEGORY_CHOICES)]
    sort = request.GET.get("sort", "new")

    qs = RestaurantProfile.objects.filter(status=RestaurantProfile.APPROVED).annotate(
        item_count=Count("menu_items", filter=Q(menu_items__is_available=True), distinct=True)
    )

    if q:
        by_item = MenuItem.objects.filter(is_available=True, name__icontains=q).values("restaurant_id")
        qs = qs.filter(Q(restaurant_name__icontains=q) | Q(city__icontains=q) | Q(pk__in=by_item))

    if selected:
        cq = Q()
        for c in selected:
            cq |= Q(category_names__icontains=c)
        qs = qs.filter(pk__in=MenuItem.objects.filter(is_available=True).filter(cq).values("restaurant_id"))

    # Veg filter removed as platform is strictly vegetarian

    qs = qs.order_by({"name": "restaurant_name", "items": "-item_count"}.get(sort, "-created_at"))

    page_obj = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "restaurants.html", {
        "page_obj": page_obj,
        "q": q, "sort": sort,
        "cuisine_options": [(v, v in selected) for v, _ in CATEGORY_CHOICES],
        "querystring": params.urlencode(),
    })

# ---------- delivery partner side ----------
def delivery_required(view):
    @login_required(login_url="base:delivery_login")
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "delivery_partner", None)
        if profile is None:
            messages.error(request, "This is not a delivery partner account.")
            return redirect("base:delivery_login")
        request.partner = profile
        return view(request, *args, **kwargs)
    return wrapper


def delivery_signup(request):
    if request.user.is_authenticated:
        return redirect("base:delivery_documents")
    if request.method == "POST":
        form = DeliveryRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Account created. Please upload your documents.")
            return redirect("base:delivery_documents")
        messages.error(request, "Please correct the errors below")
    else:
        form = DeliveryRegistrationForm()
    return render(request, "registration/delivery_signup.html", {"form": form})

class DeliveryLoginView(LoginView):

    template_name = "registration/delivery_login.html"
    authentication_form = DeliveryLoginForm
    redirect_authenticated_user = False

    def get_success_url(self):

        profile = getattr(
            self.request.user,
            "delivery_partner",
            None
        )

        if profile is not None:

            status = str(profile.status).strip().lower()

            if status == DeliveryPartnerProfile.APPROVED:
                return reverse("base:delivery_dashboard")

            return reverse("base:delivery_documents")

        return reverse("base:delivery_login")

    def get_redirect_url(self):
        """
        Ignore Django's ?next= URL for delivery partner login.

        This prevents an approved delivery partner from being
        redirected back to the documents page after login.
        """
        return None

    def form_valid(self, form):

        response = super().form_valid(form)

        if not form.cleaned_data.get("remember"):
            self.request.session.set_expiry(0)

        return response
    
def delivery_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("base:delivery_login")


@delivery_required
def delivery_documents(request):
    profile = request.partner

    # ==========================================
    # APPROVED
    # ==========================================
    # Redirect approved delivery partners directly
    # to their dashboard.
    if str(profile.status).lower() == "approved":
        return redirect("base:delivery_dashboard")

    # ==========================================
    # PENDING
    # ==========================================
    # Don't allow editing while admin is reviewing.
    if str(profile.status).lower() == "pending":
        return render(
            request,
            "delivery/documents.html",
            {
                "form": None,
                "profile": profile,
            }
        )

    # ==========================================
    # POST - SUBMIT / RESUBMIT DOCUMENTS
    # ==========================================
    if request.method == "POST":

        form = DeliveryDocumentForm(
            request.POST,
            request.FILES,
            instance=profile
        )

        if form.is_valid():

            partner = form.save(commit=False)

            # Send application for admin verification
            partner.status = DeliveryPartnerProfile.PENDING

            # Clear previous rejection reason
            partner.rejection_reason = ""

            # Submission time
            partner.submitted_at = timezone.now()

            # Clear previous review information
            partner.reviewed_at = None
            partner.reviewed_by = None

            partner.save()

            messages.success(
                request,
                "Documents submitted successfully. "
                "We'll notify you after verification."
            )

            return redirect("base:delivery_documents")

        messages.error(
            request,
            "Please correct the errors below."
        )

    # ==========================================
    # GET
    # ==========================================
    else:
        form = DeliveryDocumentForm(
            instance=profile
        )

    return render(
        request,
        "delivery/documents.html",
        {
            "form": form,
            "profile": profile,
        }
    )

@delivery_required
def delivery_dashboard(request):

    profile = request.partner

    status = str(profile.status).strip().lower()

    if status != DeliveryPartnerProfile.APPROVED:
        return redirect("base:delivery_documents")
        
    orders = Order.objects.filter(delivery_partner=profile).order_by('-updated_at')

    return render(
        request,
        "delivery/dashboard.html",
        {
            "profile": profile,
            "orders": orders,
        }
    )

@login_required
@delivery_required
@require_POST
def delivery_update_order(request, pk):
    order = get_object_or_404(Order, pk=pk, delivery_partner=request.partner)
    new_status = request.POST.get('status')
    
    valid_transitions = {
        'ready': ['out_for_delivery'],
        'out_for_delivery': ['delivered']
    }
    
    if new_status in valid_transitions.get(order.status, []):
        old_status = order.status
        order.status = new_status
        order.save()
        OrderStatusHistory.objects.create(order=order, previous_status=old_status, new_status=new_status, changed_by=request.user)
        messages.success(request, f"Order #{order.id} marked as {order.get_status_display()}.")
        
        if new_status == 'delivered':
            order.process_order_delivered()
            
    else:
        messages.error(request, "Invalid status transition.")
        
    return redirect('base:delivery_dashboard')
    
@staff_only
def delivery_requests(request):
    delivery_partners = (
        DeliveryPartnerProfile.objects
        .filter(status=DeliveryPartnerProfile.PENDING)
        .select_related("user")
        .order_by("-submitted_at")
    )

    return render(
        request,
        "dashboard/delivery_requests.html",
        {
            "delivery_partners": delivery_partners,
        },
    )


@staff_only
@require_POST
def delivery_review(request, pk):
    profile = get_object_or_404(
        DeliveryPartnerProfile,
        pk=pk
    )

    action = request.POST.get("action")
    rejection_reason = request.POST.get("rejection_reason", "").strip()

    if action == "approve":

        profile.status = DeliveryPartnerProfile.APPROVED
        profile.rejection_reason = ""
        profile.reviewed_at = timezone.now()
        profile.reviewed_by = request.user
        profile.save()

        messages.success(
            request,
            f"{profile.user.get_full_name() or profile.user.username} "
            f"has been approved as a delivery partner."
        )

    elif action == "reject":

        if not rejection_reason:
            messages.error(
                request,
                "Please provide a rejection reason."
            )

            return redirect(
                "base:delivery_detail",
                pk=profile.pk
            )

        profile.status = DeliveryPartnerProfile.REJECTED
        profile.rejection_reason = rejection_reason
        profile.reviewed_at = timezone.now()
        profile.reviewed_by = request.user
        profile.save()

        messages.success(
            request,
            "Delivery partner application rejected."
        )

    else:
        messages.error(
            request,
            "Invalid review action."
        )

    return redirect("base:delivery_requests")


@staff_only
def delivery_list(request):

    status = request.GET.get("status", "").strip()

    delivery_partners = (
        DeliveryPartnerProfile.objects
        .select_related("user", "reviewed_by")
        .order_by("-created_at")
    )

    if status in [
        DeliveryPartnerProfile.INCOMPLETE,
        DeliveryPartnerProfile.PENDING,
        DeliveryPartnerProfile.APPROVED,
        DeliveryPartnerProfile.REJECTED,
    ]:
        delivery_partners = delivery_partners.filter(
            status=status
        )

    return render(
        request,
        "dashboard/delivery_list.html",
        {
            "delivery_partners": delivery_partners,
            "selected_status": status,
        },
    )


@staff_only
def delivery_detail(request, pk):

    profile = get_object_or_404(
        DeliveryPartnerProfile.objects.select_related(
            "user",
            "reviewed_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "dashboard/delivery_detail.html",
        {
            "profile": profile,
        },
    )

@login_required
def add_to_cart(request, pk):
    if request.method != "POST":
        messages.info(request, "Please click 'Add to Cart' again to confirm your action.")
        return redirect("base:menu_item_public", pk=pk)

    menu_item = get_object_or_404(MenuItem, pk=pk)
    
    if not menu_item.is_available:
        messages.error(request, "This item is currently unavailable.")
        return redirect("base:restaurant_public", pk=menu_item.restaurant.id)
        
    if menu_item.restaurant.status != RestaurantProfile.APPROVED:
        messages.error(request, "This restaurant is currently not accepting orders.")
        return redirect("base:restaurant_public", pk=menu_item.restaurant.id)
    
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    if cart.restaurant and cart.restaurant != menu_item.restaurant and cart.items.exists():
        messages.error(request, "Your cart contains items from a different restaurant. Please clear your cart first to add items from here.")
        return redirect("base:restaurant_public", pk=menu_item.restaurant.id)
        
    cart.restaurant = menu_item.restaurant
    cart.save()
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, menu_item=menu_item)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        
    messages.success(request, f"Added {menu_item.name} to cart.")
    return redirect("base:restaurant_public", pk=menu_item.restaurant.id)

@login_required
def view_cart(request):
    cart, _ = Cart.objects.prefetch_related('items__menu_item').get_or_create(user=request.user)
    items = cart.items.all()
    
    subtotal_taxable = sum(item.taxable_value for item in items)
    total_cgst = sum(item.cgst_amount for item in items)
    total_sgst = sum(item.sgst_amount for item in items)
    total_gst = total_cgst + total_sgst
    subtotal_with_tax = sum(item.item_total for item in items)
    
    delivery_fee = Decimal('30.00') if items else Decimal('0.00')
    total = subtotal_with_tax + delivery_fee
    
    context = {
        'cart': cart,
        'items': items,
        'subtotal': subtotal_taxable,
        'gst': total_gst,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'delivery_fee': delivery_fee,
        'total': total,
    }
    return render(request, "cart.html", context)

@login_required
@require_POST
def update_cart_item(request, pk):
    cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    action = request.POST.get('action')
    
    if action == 'increase':
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            
    return redirect("base:view_cart")

@login_required
@require_POST
def remove_cart_item(request, pk):
    cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    cart_item.delete()
    return redirect("base:view_cart")

auth_api = 'https://api-preprod.phonepe.com/apis/pg-sandbox'
pg_api = 'https://api-preprod.phonepe.com/apis/pg-sandbox'
client_id = "TEST-M22ERCW4AOPJ5_25050"
client_secret = "ZWQ0YTk0ZTAtNWQwZi00ODM1LWFhNDctNjFiOTgwZjg3ZWRi"
client_version = "1"
redirect_url = "http://127.0.0.1:8000"

@login_required
def checkout(request):
    cart, _ = Cart.objects.prefetch_related('items__menu_item').get_or_create(user=request.user)
    items = cart.items.all()
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("base:view_cart")
        
    subtotal_taxable = sum(item.taxable_value for item in items)
    total_cgst = sum(item.cgst_amount for item in items)
    total_sgst = sum(item.sgst_amount for item in items)
    total_gst = total_cgst + total_sgst
    subtotal_with_tax = sum(item.item_total for item in items)
    
    delivery_fee = Decimal('30.00')
    total = subtotal_with_tax + delivery_fee
    
    addresses = request.user.addresses.all()
    
    if request.method == "POST":
        address_id = request.POST.get("address_id")
        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect("base:checkout")
            
        address = get_object_or_404(CustomerAddress, pk=address_id, user=request.user)
        
        with transaction.atomic():
            txn_id = f"TXN_{uuid.uuid4().hex[:16].upper()}"
            order = Order.objects.create(
                user=request.user,
                restaurant=cart.restaurant,
                delivery_address=address,
                delivery_address_text=f"{address.recipient_name}, {address.house_flat_no}, {address.street_area}, {address.city}, {address.state} - {address.pin_code}. Ph: {address.phone_number}",
                subtotal=subtotal_taxable,
                gst=total_gst,
                taxable_subtotal=subtotal_taxable,
                total_cgst=total_cgst,
                total_sgst=total_sgst,
                delivery_fee=delivery_fee,
                wallet_applied=Decimal('0.00'),
                total_amount=total,
                status="pending",
                payment_status="pending",
                transaction_id=txn_id
            )
            
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    menu_item=item.menu_item,
                    item_name=item.menu_item.name,
                    serving_unit=item.menu_item.serving_unit,
                    pieces_per_serving=item.menu_item.pieces_per_serving,
                    quantity_in_grams_or_ml=item.menu_item.quantity_in_grams_or_ml,
                    price=item.menu_item.price,
                    quantity=item.quantity,
                    total=item.item_total,
                    taxable_value=item.taxable_value,
                    cgst_rate=item.menu_item.cgst_rate,
                    sgst_rate=item.menu_item.sgst_rate,
                    cgst_amount=item.cgst_amount,
                    sgst_amount=item.sgst_amount,
                    tax_inclusive=item.menu_item.tax_inclusive
                )
                
        return redirect("base:pay", order_id=order.id)
        
    context = {
        'items': items,
        'subtotal': subtotal_taxable,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'gst': total_gst,
        'delivery_fee': delivery_fee,
        'total': total,
        'addresses': addresses,
    }
    return render(request, "checkout.html", context)

@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "order_success.html", {"order": order})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    # Ownership checks
    is_owner = (order.user == request.user)
    is_restaurant = hasattr(request.user, 'restaurant') and getattr(request.user, 'restaurant', None) == order.restaurant
    is_admin = request.user.is_superuser
    
    if not (is_owner or is_restaurant or is_admin):
        messages.error(request, "You do not have permission to view this order.")
        return redirect("base:home")
        
    return render(request, "order_detail.html", {"order": order})

@login_required
def pay(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != "pending" or order.payment_status == "success":
        messages.error(request, "Order is not ready for payment.")
        return redirect("base:order_detail", pk=order.id)

    token_res = requests.post(
        auth_api + "/v1/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "client_version": client_version,
            "grant_type": "client_credentials",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    token_data = token_res.json()

    if "access_token" not in token_data:
        messages.error(request, "Payment authentication failed")
        return redirect("base:order_detail", pk=order.id)

    token = token_data["access_token"]

    response = requests.post(
        pg_api + "/checkout/v2/pay",
        json={
            "merchantOrderId": str(order.id),
            "amount": int(order.total_amount * 100),
            "paymentFlow": {
                "type": "PG_CHECKOUT",
                "merchantUrls": {
                    "redirectUrl": f"{redirect_url}/payment-return/{order.id}/"
                }
            }
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"O-Bearer {token}",
        }
    )

    data = response.json()

    if "redirectUrl" in data:
        return render(request, "pay.html", {"outputurl": data["redirectUrl"]})

    messages.error(request, "Unable to start payment")
    return redirect("base:order_detail", pk=order.id)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@login_required
def payment_return(request, uid):
    order = Order.objects.filter(id=uid, user=request.user).first()
    if not order:
        messages.error(request, "Order not found or session expired")
        return redirect("base:checkout")

    token_res = requests.post(
        auth_api + "/v1/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "client_version": client_version,
            "grant_type": "client_credentials",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        token_data = token_res.json()
    except Exception:
        messages.error(request, "Payment verification failed (token error)")
        return redirect("base:checkout")

    if "access_token" not in token_data:
        messages.error(request, "Payment verification failed")
        return redirect("base:checkout")

    token = token_data["access_token"]

    status_res = requests.get(
        f"{pg_api}/checkout/v2/order/{uid}/status",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"O-Bearer {token}",
        }
    )

    try:
        data = status_res.json()
    except Exception:
        order.payment_status = "failed"
        order.save()
        messages.error(request, "Payment failed or cancelled")
        return redirect("base:checkout")

    if data.get("state") == "COMPLETED":
        if order.payment_status != "success":
            order.payment_status = "success"
            old_status = order.status
            order.status = "paid"
            order.transaction_id = data.get("orderId")
            order.save()
            OrderStatusHistory.objects.create(order=order, previous_status=old_status, new_status="paid")

            # Process financial records
            order.process_payment_success()

            Cart.objects.filter(user=request.user).delete()

        messages.success(request, "Payment successful")
        return redirect("base:order_success", pk=order.id)

    order.payment_status = "failed"
    order.save()
    messages.error(request, "Payment failed or cancelled")
    return redirect("base:checkout")

@login_required
def wallet_view(request):
    wallet, _ = CustomerWallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by('-created_at')
    return render(request, "wallet.html", {
        "wallet": wallet,
        "transactions": transactions
    })

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "order_history.html", {"orders": orders})

@login_required
@restaurant_required
def restaurant_earnings_dashboard(request):
    restaurant = request.restaurant
    earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=restaurant)
    
    # Wallet Transactions
    transactions = LedgerEntry.objects.filter(order__restaurant=restaurant).order_by('-created_at')
    
    return render(request, "restaurant_earnings.html", {
        "earnings": earnings,
        "transactions": transactions,
    })

def admin_financial_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect("base:home")
        
    ledgers = LedgerEntry.objects.all().order_by('-created_at')
    withdrawals = WithdrawalRequest.objects.all().order_by('-created_at')
    
    total_sales = LedgerEntry.objects.filter(transaction_type='order_payment').aggregate(models.Sum('eligible_food_subtotal'))['eligible_food_subtotal__sum'] or Decimal('0.00')
    total_commission = LedgerEntry.objects.filter(transaction_type='order_payment').aggregate(models.Sum('platform_commission'))['platform_commission__sum'] or Decimal('0.00')
    total_earnings = LedgerEntry.objects.filter(transaction_type='order_payment').aggregate(models.Sum('restaurant_earnings'))['restaurant_earnings__sum'] or Decimal('0.00')
    
    if request.method == "POST":
        action = request.POST.get("action")
        req_id = request.POST.get("request_id")
        notes = request.POST.get("admin_notes", "")
        ref = request.POST.get("payout_reference", "")
        rej_reason = request.POST.get("rejection_reason", "")
        
        wr = get_object_or_404(WithdrawalRequest, id=req_id)
        
        if action == "approve" and wr.status == "pending":
            wr.status = "approved"
            wr.admin_notes = notes
            wr.save()
            messages.success(request, f"Request #{wr.id} approved.")
            
        elif action == "pay" and wr.status == "approved":
            if not ref:
                messages.error(request, "Payout reference is required to mark as paid.")
            else:
                with transaction.atomic():
                    wr.status = "paid"
                    wr.payout_reference = ref
                    wr.admin_notes = notes
                    wr.save()
                    
                    e = RestaurantEarnings.objects.select_for_update().get(restaurant=wr.restaurant)
                    if e.reserved_balance >= wr.amount:
                        e.reserved_balance -= wr.amount
                        e.withdrawn_balance += wr.amount
                        e.save()
                messages.success(request, f"Request #{wr.id} marked as paid.")
                
        elif action == "reject" and wr.status in ["pending", "approved"]:
            if not rej_reason:
                messages.error(request, "Rejection reason is required.")
            else:
                with transaction.atomic():
                    wr.status = "rejected"
                    wr.admin_notes = notes
                    wr.rejection_reason = rej_reason
                    wr.save()
                    
                    # Refund balance back from reserved
                    e = RestaurantEarnings.objects.select_for_update().get(restaurant=wr.restaurant)
                    if e.reserved_balance >= wr.amount:
                        e.reserved_balance -= wr.amount
                        e.available_balance += wr.amount
                        e.save()
                messages.success(request, f"Request #{wr.id} rejected and funds restored.")
                
        return redirect("base:admin_financial_dashboard")
        
    return render(request, "admin_financial_dashboard.html", {
        "ledgers": ledgers,
        "withdrawals": withdrawals,
        "total_sales": total_sales,
        "total_commission": total_commission,
        "total_earnings": total_earnings,
    })

@login_required
def admin_ledger_detail(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect("base:home")
        
    entry = get_object_or_404(LedgerEntry, id=pk)
    return render(request, "admin_ledger_detail.html", {
        "entry": entry,
        "order": entry.order
    })

@staff_only
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at').prefetch_related('items__menu_item', 'ledger_entries')
    partners = DeliveryPartnerProfile.objects.filter(status=DeliveryPartnerProfile.APPROVED, is_online=True)
    return render(request, "dashboard/orders.html", {"orders": orders, "partners": partners})

@staff_only
@require_POST
def admin_assign_delivery(request, pk):
    order = get_object_or_404(Order, pk=pk)
    partner_id = request.POST.get('partner_id')
    
    if order.status != 'ready':
        messages.error(request, "Can only assign delivery partners to orders ready for pickup.")
        return redirect('base:admin_orders')
        
    partner = get_object_or_404(DeliveryPartnerProfile, pk=partner_id, status=DeliveryPartnerProfile.APPROVED)
    order.delivery_partner = partner
    order.save()
    messages.success(request, f"Order #{order.id} assigned to {partner.user.get_full_name() or partner.user.username}.")
    return redirect('base:admin_orders')

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@login_required
def track_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    status_history = order.status_history.all().order_by('-timestamp')
    return render(request, "order_tracking.html", {"order": order, "status_history": status_history})

@login_required
def get_live_location(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if not order.delivery_partner:
        return JsonResponse({"error": "No delivery partner assigned"}, status=400)
    try:
        loc = order.delivery_partner.location
        return JsonResponse({"lat": loc.latitude, "lng": loc.longitude, "updated_at": loc.last_updated})
    except Exception:
        return JsonResponse({"error": "Location not available"}, status=404)

@csrf_exempt
@login_required
def delivery_update_location(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lat = data.get("lat")
            lng = data.get("lng")
            if hasattr(request.user, "delivery_profile"):
                loc, _ = DeliveryPartnerLocation.objects.update_or_create(
                    partner=request.user.delivery_profile,
                    defaults={"latitude": lat, "longitude": lng}
                )
                return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
@staff_only
def admin_restaurant_wallets(request):
    wallets = RestaurantEarnings.objects.select_related('restaurant').all()
    return render(request, 'admin_restaurant_wallets.html', {'wallets': wallets})

@staff_only
def admin_commission_history(request):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect("base:home")
    ledgers = LedgerEntry.objects.filter(transaction_type='order_payment').order_by('-created_at').select_related('order__user', 'order__restaurant').prefetch_related('order__items__menu_item')
    return render(request, "admin_commission_history.html", {"ledgers": ledgers})

@restaurant_required
def restaurant_commission_history(request):
    profile = request.restaurant
    ledgers = LedgerEntry.objects.filter(transaction_type='order_payment', order__restaurant=profile).order_by('-created_at').select_related('order__user').prefetch_related('order__items__menu_item')
    return render(request, "restaurant_commission_history.html", {"ledgers": ledgers})

@restaurant_required
def restaurant_payout_settings(request):
    restaurant = request.restaurant
    settings, _ = RestaurantPayoutSettings.objects.get_or_create(restaurant=restaurant)
    earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=restaurant)
    withdrawals = restaurant.withdrawals.all().order_by('-created_at')
    
    # Check if a withdrawal was made this week (last 7 days)
    import datetime
    from django.utils import timezone
    seven_days_ago = timezone.now() - datetime.timedelta(days=7)
    recent_withdrawal = restaurant.withdrawals.filter(created_at__gte=seven_days_ago).first()
    can_withdraw = recent_withdrawal is None
    
    if request.method == "POST":
        if "amount" in request.POST:
            amount_str = request.POST.get("amount")
            from decimal import Decimal
            try:
                amount = Decimal(amount_str)
                if amount <= 0:
                    messages.error(request, "Invalid withdrawal amount.")
                elif amount > earnings.available_balance:
                    messages.error(request, "Insufficient available balance.")
                elif not can_withdraw:
                    messages.error(request, "You can only request one withdrawal per week.")
                elif settings.get_snapshot() == "Not set":
                    messages.error(request, "Please configure your payout settings first.")
                else:
                    from django.db import transaction
                    with transaction.atomic():
                        e = RestaurantEarnings.objects.select_for_update().get(id=earnings.id)
                        if amount <= e.available_balance:
                            e.available_balance -= amount
                            e.reserved_balance += amount
                            e.save()
                            
                            WithdrawalRequest.objects.create(
                                restaurant=restaurant,
                                amount=amount,
                                destination_details=settings.get_snapshot(),
                                status="pending"
                            )
                            messages.success(request, "Withdrawal request submitted successfully.")
                            return redirect("base:restaurant_payout_settings")
                        else:
                            messages.error(request, "Insufficient available balance.")
            except Exception as e:
                messages.error(request, f"Error processing withdrawal: {str(e)}")
        else:
            payout_method = request.POST.get("payout_method")
            
            # Bank Details
            bank_name = request.POST.get("bank_name", "")
            account_number = request.POST.get("account_number", "")
            ifsc_code = request.POST.get("ifsc_code", "")
            account_holder_name = request.POST.get("account_holder_name", "")
            
            # UPI Details
            upi_id = request.POST.get("upi_id", "")
            upi_account_holder_name = request.POST.get("upi_account_holder_name", "")
            
            # QR image
            qr_image = request.FILES.get("qr_code_image")
            
            settings.payout_method = payout_method
            settings.bank_name = bank_name
            settings.account_number = account_number
            settings.ifsc_code = ifsc_code
            settings.account_holder_name = account_holder_name
            settings.upi_id = upi_id
            settings.upi_account_holder_name = upi_account_holder_name
            
            if qr_image:
                settings.qr_code_image = qr_image
                
            settings.save()
            messages.success(request, "Payout settings updated successfully.")
            return redirect("base:restaurant_payout_settings")
            
    payout_ready = settings.get_snapshot() != 'Not set'
    payout_snapshot = settings.get_snapshot() if payout_ready else ''
            
    return render(request, "restaurant_payout_settings.html", {
        "settings": settings,
        "earnings": earnings,
        "withdrawals": withdrawals,
        "can_withdraw": can_withdraw,
        "recent_withdrawal": recent_withdrawal,
        "payout_ready": payout_ready,
        "payout_snapshot": payout_snapshot
    })



@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Ownership checks
    is_owner = (order.user == request.user)
    is_restaurant = hasattr(request.user, 'restaurant') and getattr(request.user, 'restaurant', None) == order.restaurant
    is_admin = request.user.is_superuser
    
    if not (is_owner or is_restaurant or is_admin):
        messages.error(request, "You do not have permission to view this invoice.")
        return redirect("base:home")
        
    context = {
        'order': order,
        'restaurant': order.restaurant,
        'customer': order.user,
        'is_download': request.GET.get('download', '') == 'true'
    }
    
    if context['is_download']:
        pdf = render_to_pdf('invoice.html', context)
        if pdf:
            response = HttpResponse(pdf.content, content_type='application/pdf')
            filename = f"UrbanFoods_Invoice_{order.id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        return HttpResponse("Error Generating PDF", status=400)
    
    return render(request, 'invoice.html', context)


@login_required
@restaurant_required
def restaurant_all_orders(request):
    if request.restaurant.status != 'approved':
        return redirect("base:restaurant_documents")
    orders = Order.objects.filter(restaurant=request.restaurant).exclude(payment_status='pending').order_by('-created_at')
    orders = orders.prefetch_related('items__menu_item', 'ledger_entries')
    return render(request, "restaurant/all_orders.html", {"orders": orders})
