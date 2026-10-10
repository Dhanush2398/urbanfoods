from django.utils import timezone
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import Http404, JsonResponse
from django.db.models import Count, Q, Sum
from decimal import Decimal
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
import json
import base64
import hashlib
import requests
import uuid
from decimal import InvalidOperation
from datetime import timedelta
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
    LedgerEntry, WithdrawalRequest, RestaurantEarnings, CustomerWallet,
    CustomerWalletTransaction, RestaurantPayoutSettings
)
from django.core.paginator import Paginator
staff_only = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="base:login")

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


# ---------- customer wallet and orders ----------
@login_required
def wallet_view(request):
    wallet, _ = CustomerWallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.order_by("-created_at")
    return render(request, "wallet.html", {
        "wallet": wallet,
        "transactions": transactions,
    })


@login_required
def order_history(request):
    orders = (
        Order.objects.filter(user=request.user)
        .select_related("restaurant", "delivery_address")
        .prefetch_related("items__menu_item")
        .order_by("-created_at")
    )
    return render(request, "order_history.html", {"orders": orders})


@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related("menu_item").all()
    subtotal = sum((item.taxable_value for item in items), Decimal("0.00"))
    cgst = sum((item.cgst_amount for item in items), Decimal("0.00"))
    sgst = sum((item.sgst_amount for item in items), Decimal("0.00"))
    gst = cgst + sgst
    delivery_fee = Decimal("40.00") if items.exists() else Decimal("0.00")
    return render(request, "cart.html", {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "gst": gst,
        "delivery_fee": delivery_fee,
        "total": subtotal + gst + delivery_fee,
    })


@login_required
@require_POST
def add_to_cart(request, pk):
    menu_item = get_object_or_404(
        MenuItem.objects.select_related("restaurant"),
        pk=pk,
        is_available=True,
        restaurant__status=RestaurantProfile.APPROVED,
    )
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if cart.restaurant_id and cart.restaurant_id != menu_item.restaurant_id:
        cart.items.all().delete()
    cart.restaurant = menu_item.restaurant
    cart.save(update_fields=["restaurant", "updated_at"])
    item, created = CartItem.objects.get_or_create(cart=cart, menu_item=menu_item)
    if not created:
        item.quantity += 1
        item.save(update_fields=["quantity"])
    messages.success(request, f"{menu_item.name} added to your cart.")
    return redirect("base:view_cart")


@login_required
@require_POST
def update_cart_item(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    if request.POST.get("action") == "increase":
        item.quantity += 1
        item.save(update_fields=["quantity"])
    elif request.POST.get("action") == "decrease":
        if item.quantity <= 1:
            item.delete()
        else:
            item.quantity -= 1
            item.save(update_fields=["quantity"])
    else:
        messages.error(request, "Invalid cart update.")
    return redirect("base:view_cart")


@login_required
@require_POST
def remove_cart_item(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    cart = item.cart
    item.delete()
    if not cart.items.exists():
        cart.restaurant = None
        cart.save(update_fields=["restaurant", "updated_at"])
    return redirect("base:view_cart")


@login_required
def checkout(request):
    cart = get_object_or_404(Cart.objects.select_related("restaurant"), user=request.user)
    items = list(cart.items.select_related("menu_item").all())
    if not items or cart.restaurant is None:
        messages.error(request, "Your cart is empty.")
        return redirect("base:view_cart")
    addresses = request.user.addresses.all()
    if request.method == "POST":
        address = get_object_or_404(
            CustomerAddress,
            pk=request.POST.get("address_id"),
            user=request.user,
        )
        with transaction.atomic():
            subtotal = sum((item.taxable_value for item in items), Decimal("0.00"))
            cgst = sum((item.cgst_amount for item in items), Decimal("0.00"))
            sgst = sum((item.sgst_amount for item in items), Decimal("0.00"))
            gst = cgst + sgst
            delivery_fee = Decimal("40.00")
            total = subtotal + gst + delivery_fee
            address_text = (
                f"{address.recipient_name}, {address.house_flat_no}, "
                f"{address.street_area}, {address.city}, {address.state} "
                f"{address.pin_code}, Phone: {address.phone_number}"
            )
            order = Order.objects.create(
                user=request.user,
                restaurant=cart.restaurant,
                delivery_address=address,
                delivery_address_text=address_text,
                subtotal=subtotal,
                gst=gst,
                taxable_subtotal=subtotal,
                total_cgst=cgst,
                total_sgst=sgst,
                delivery_fee=delivery_fee,
                total_amount=total,
                transaction_id=uuid.uuid4().hex.upper(),
            )
            OrderItem.objects.bulk_create([
                OrderItem(
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
                    tax_inclusive=item.menu_item.tax_inclusive,
                )
                for item in items
            ])
            cart.items.all().delete()
            cart.restaurant = None
            cart.save(update_fields=["restaurant", "updated_at"])
        return redirect("base:pay", order_id=order.pk)

    subtotal = sum((item.taxable_value for item in items), Decimal("0.00"))
    cgst = sum((item.cgst_amount for item in items), Decimal("0.00"))
    sgst = sum((item.sgst_amount for item in items), Decimal("0.00"))
    gst = cgst + sgst
    delivery_fee = Decimal("40.00")
    return render(request, "checkout.html", {
        "cart": cart,
        "restaurant": cart.restaurant,
        "items": items,
        "addresses": addresses,
        "subtotal": subtotal,
        "gst": gst,
        "delivery_fee": delivery_fee,
        "total": subtotal + gst + delivery_fee,
    })


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user, payment_status="success")
    return render(request, "order_success.html", {"order": order})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("restaurant", "delivery_address"),
        pk=pk,
        user=request.user,
    )
    return render(request, "order_detail.html", {"order": order})


@login_required
def track_order(request, pk):
    order = get_object_or_404(
        Order.objects.select_related(
            "restaurant", "delivery_address", "delivery_partner__user"
        ).prefetch_related("items", "status_history"),
        pk=pk,
        user=request.user,
    )
    return render(request, "order_tracking.html", {
        "order": order,
        "status_history": order.status_history.order_by("timestamp"),
    })


@login_required
@require_GET
def get_live_location(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.delivery_partner_id is None:
        return JsonResponse({"detail": "Delivery location is not available."}, status=404)
    location = get_object_or_404(DeliveryPartnerLocation, partner=order.delivery_partner)
    return JsonResponse({
        "lat": float(location.latitude),
        "lng": float(location.longitude),
        "updated_at": location.last_updated.isoformat(),
    })


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("restaurant", "user", "delivery_address"),
        pk=order_id,
    )
    if order.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    response = render(request, "invoice.html", {
        "order": order,
        "restaurant": order.restaurant,
        "customer": order.user,
    })
    if request.GET.get("download") == "true":
        response["Content-Disposition"] = f'attachment; filename="invoice_{order.pk}.html"'
    return response


@login_required
def pay(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.payment_status == "success":
        return redirect("base:order_success", pk=order.pk)
    if not settings.PHONEPE_MERCHANT_ID or not settings.PHONEPE_SALT_KEY:
        messages.error(request, "Online payment is not configured. Please contact support.")
        return redirect("base:order_detail", pk=order.pk)

    api_path = "/pg/v1/pay"
    api_host = (
        "https://api-preprod.phonepe.com/apis/pg-sandbox"
        if settings.PHONEPE_ENV.upper() == "UAT"
        else "https://api.phonepe.com/apis/hermes"
    )
    return_url = request.build_absolute_uri(reverse("base:payment_return", args=[order.pk]))
    payload = {
        "merchantId": settings.PHONEPE_MERCHANT_ID,
        "merchantTransactionId": order.transaction_id,
        "merchantUserId": str(request.user.pk),
        "amount": int(order.total_amount * 100),
        "redirectUrl": return_url,
        "redirectMode": "POST",
        "callbackUrl": return_url,
        "paymentInstrument": {"type": "PAY_PAGE"},
    }
    encoded_payload = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    signature = hashlib.sha256(
        f"{encoded_payload}{api_path}{settings.PHONEPE_SALT_KEY}".encode("utf-8")
    ).hexdigest()
    try:
        response = requests.post(
            f"{api_host}{api_path}",
            json={"request": encoded_payload},
            headers={"Content-Type": "application/json",
                     "X-VERIFY": f"{signature}###{settings.PHONEPE_SALT_INDEX}"},
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException:
        messages.error(request, "The payment provider could not be reached. Please retry.")
        return redirect("base:order_detail", pk=order.pk)
    except ValueError:
        messages.error(request, "The payment provider returned an invalid response.")
        return redirect("base:order_detail", pk=order.pk)

    redirect_url = (
        result.get("data", {}).get("instrumentResponse", {}).get("redirectInfo", {}).get("url")
        if result.get("success")
        else None
    )
    if not redirect_url:
        messages.error(request, result.get("message") or "Unable to start payment.")
        return redirect("base:order_detail", pk=order.pk)
    return redirect(redirect_url)


@csrf_exempt
def payment_return(request, uid):
    order = get_object_or_404(Order, pk=uid)
    if not settings.PHONEPE_MERCHANT_ID or not settings.PHONEPE_SALT_KEY:
        messages.error(request, "Payment status could not be verified.")
        return redirect("base:order_detail", pk=order.pk)
    api_path = (
        f"/pg/v1/status/{settings.PHONEPE_MERCHANT_ID}/{order.transaction_id}"
    )
    api_host = (
        "https://api-preprod.phonepe.com/apis/pg-sandbox"
        if settings.PHONEPE_ENV.upper() == "UAT"
        else "https://api.phonepe.com/apis/hermes"
    )
    signature = hashlib.sha256(
        f"{api_path}{settings.PHONEPE_SALT_KEY}".encode("utf-8")
    ).hexdigest()
    try:
        response = requests.get(
            f"{api_host}{api_path}",
            headers={"Content-Type": "application/json",
                     "X-VERIFY": f"{signature}###{settings.PHONEPE_SALT_INDEX}",
                     "X-MERCHANT-ID": settings.PHONEPE_MERCHANT_ID},
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException:
        messages.error(request, "The payment provider could not be reached to verify payment.")
        return redirect("base:order_detail", pk=order.pk)
    except ValueError:
        messages.error(request, "The payment provider returned an invalid status response.")
        return redirect("base:order_detail", pk=order.pk)

    data = result.get("data", {})
    if result.get("success") and data.get("responseCode") == "PAYMENT_SUCCESS":
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.payment_status != "success":
                order.payment_status = "success"
                order.status = "paid"
                order.provider_reference_id = data.get("transactionId", "")
                order.save(update_fields=[
                    "payment_status", "status", "provider_reference_id", "updated_at"
                ])
                order.process_payment_success()
        return redirect("base:order_success", pk=order.pk)
    if data.get("responseCode") in {"PAYMENT_ERROR", "PAYMENT_DECLINED"}:
        order.payment_status = "failed"
        order.save(update_fields=["payment_status", "updated_at"])
        messages.error(request, "Payment was not successful. You may retry.")
    else:
        messages.info(request, "Payment is still being processed.")
    return redirect("base:order_detail", pk=order.pk)


# ---------- restaurant financials ----------
@restaurant_required
def restaurant_earnings_dashboard(request):
    if request.restaurant.status != RestaurantProfile.APPROVED:
        return redirect("base:restaurant_documents")
    earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=request.restaurant)
    transactions = (
        LedgerEntry.objects.filter(order__restaurant=request.restaurant)
        .select_related("order")
        .order_by("-created_at")
    )
    return render(request, "restaurant_earnings.html", {
        "earnings": earnings,
        "transactions": transactions,
        "ledgers": transactions.filter(transaction_type="order_payment"),
    })


@restaurant_required
def restaurant_commission_history(request):
    if request.restaurant.status != RestaurantProfile.APPROVED:
        return redirect("base:restaurant_documents")
    ledgers = (
        LedgerEntry.objects.filter(
            order__restaurant=request.restaurant,
            transaction_type="order_payment",
        )
        .select_related("order", "order__user", "order__restaurant")
        .prefetch_related("order__items")
        .order_by("-created_at")
    )
    return render(request, "restaurant_commission_history.html", {"ledgers": ledgers})


@restaurant_required
def restaurant_all_orders(request):
    if request.restaurant.status != RestaurantProfile.APPROVED:
        return redirect("base:restaurant_documents")
    orders = (
        Order.objects.filter(restaurant=request.restaurant)
        .select_related("user", "delivery_address", "delivery_partner")
        .prefetch_related("items__menu_item", "ledger_entries")
        .order_by("-created_at")
    )
    return render(request, "restaurant/all_orders.html", {"orders": orders})


def _payout_settings_ready(payout_settings):
    if payout_settings.payout_method == "bank":
        return all((
            payout_settings.bank_name,
            payout_settings.account_holder_name,
            payout_settings.account_number,
            payout_settings.ifsc_code,
        ))
    if payout_settings.payout_method == "upi":
        return bool(payout_settings.upi_id and payout_settings.upi_account_holder_name)
    return bool(payout_settings.qr_code_image)


@restaurant_required
def restaurant_payout_settings(request):
    if request.restaurant.status != RestaurantProfile.APPROVED:
        return redirect("base:restaurant_documents")

    payout_settings, _ = RestaurantPayoutSettings.objects.get_or_create(
        restaurant=request.restaurant
    )
    earnings, _ = RestaurantEarnings.objects.get_or_create(restaurant=request.restaurant)
    withdrawals = request.restaurant.withdrawals.order_by("-created_at")
    recent_withdrawal = withdrawals.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).first()

    if request.method == "POST" and "amount" in request.POST:
        try:
            amount = Decimal(request.POST.get("amount", "").strip())
        except (InvalidOperation, ValueError):
            messages.error(request, "Enter a valid withdrawal amount.")
            return redirect("base:restaurant_payout_settings")
        if (not amount.is_finite() or amount <= 0 or amount.adjusted() > 9):
            messages.error(request, "Enter a positive withdrawal amount within the supported range.")
            return redirect("base:restaurant_payout_settings")
        try:
            has_fractional_paisa = amount != amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            has_fractional_paisa = True
        if has_fractional_paisa:
            messages.error(request, "Withdrawal amounts may have at most two decimal places.")
            return redirect("base:restaurant_payout_settings")
        if not _payout_settings_ready(payout_settings):
            messages.error(request, "Complete payout settings before requesting a withdrawal.")
            return redirect("base:restaurant_payout_settings")

        with transaction.atomic():
            locked_earnings = RestaurantEarnings.objects.select_for_update().get(
                restaurant=request.restaurant
            )
            recent_withdrawal = request.restaurant.withdrawals.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()
            if recent_withdrawal:
                messages.error(request, "You can submit a withdrawal request once every seven days.")
            elif amount > locked_earnings.available_balance:
                messages.error(request, "The requested amount exceeds your available balance.")
            else:
                withdrawal = WithdrawalRequest.objects.create(
                    restaurant=request.restaurant,
                    amount=amount,
                    destination_details=payout_settings.get_snapshot(),
                )
                locked_earnings.available_balance -= amount
                locked_earnings.reserved_balance += amount
                locked_earnings.save(update_fields=[
                    "available_balance", "reserved_balance", "updated_at"
                ])
                messages.success(request, f"Withdrawal request #{withdrawal.pk} submitted.")
        return redirect("base:restaurant_payout_settings")

    if request.method == "POST":
        method = request.POST.get("payout_method", "")
        if method not in dict(RestaurantPayoutSettings.PAYOUT_METHOD_CHOICES):
            messages.error(request, "Select a valid payout method.")
        else:
            payout_settings.payout_method = method
            payout_settings.account_holder_name = request.POST.get("account_holder_name", "").strip()
            payout_settings.bank_name = request.POST.get("bank_name", "").strip()
            payout_settings.account_number = request.POST.get("account_number", "").strip()
            payout_settings.ifsc_code = request.POST.get("ifsc_code", "").strip().upper()
            payout_settings.upi_id = request.POST.get("upi_id", "").strip()
            payout_settings.upi_account_holder_name = request.POST.get(
                "upi_account_holder_name", ""
            ).strip()
            if "qr_code_image" in request.FILES:
                payout_settings.qr_code_image = request.FILES["qr_code_image"]
            payout_settings.save()
            messages.success(request, "Payout settings saved.")
        return redirect("base:restaurant_payout_settings")

    return render(request, "restaurant_payout_settings.html", {
        "settings": payout_settings,
        "earnings": earnings,
        "withdrawals": withdrawals,
        "recent_withdrawal": recent_withdrawal,
        "can_withdraw": recent_withdrawal is None,
        "payout_ready": _payout_settings_ready(payout_settings),
        "payout_snapshot": payout_settings.get_snapshot(),
    })


# ---------- admin financials ----------
@staff_only
def admin_financial_dashboard(request):
    if request.method == "POST":
        try:
            request_id = int(request.POST.get("request_id", ""))
        except ValueError:
            messages.error(request, "Invalid withdrawal request.")
            return redirect("base:admin_financial_dashboard")
        action = request.POST.get("action")
        with transaction.atomic():
            withdrawal = get_object_or_404(
                WithdrawalRequest.objects.select_for_update().select_related("restaurant"),
                pk=request_id,
            )
            earnings = get_object_or_404(
                RestaurantEarnings.objects.select_for_update(),
                restaurant=withdrawal.restaurant,
            )
            if action == "approve" and withdrawal.status == "pending":
                withdrawal.status = "approved"
                withdrawal.admin_notes = f"Approved by {request.user.get_username()}."
                withdrawal.save(update_fields=["status", "admin_notes", "updated_at"])
                messages.success(request, f"Withdrawal #{withdrawal.pk} approved.")
            elif action == "pay" and withdrawal.status == "approved":
                reference = request.POST.get("payout_reference", "").strip()
                if not reference:
                    messages.error(request, "Enter the payout transaction reference.")
                else:
                    if earnings.reserved_balance < withdrawal.amount:
                        messages.error(request, "Reserved balance is insufficient; payout was not recorded.")
                    else:
                        withdrawal.status = "paid"
                        withdrawal.payout_reference = reference
                        withdrawal.save(update_fields=[
                            "status", "payout_reference", "updated_at"
                        ])
                        earnings.reserved_balance -= withdrawal.amount
                        earnings.withdrawn_balance += withdrawal.amount
                        earnings.save(update_fields=[
                            "reserved_balance", "withdrawn_balance", "updated_at"
                        ])
                        LedgerEntry.objects.create(
                            reference=f"WD_{withdrawal.pk}_{uuid.uuid4().hex[:8].upper()}",
                            amount=withdrawal.amount,
                            currency="INR",
                            restaurant_earnings=withdrawal.amount,
                            transaction_type="withdrawal",
                            direction="debit",
                            status="completed",
                        )
                        messages.success(request, f"Withdrawal #{withdrawal.pk} marked as paid.")
            elif action == "reject" and withdrawal.status in {"pending", "approved"}:
                reason = request.POST.get("rejection_reason", "").strip()
                if not reason:
                    messages.error(request, "Enter a reason for rejecting the withdrawal.")
                elif earnings.reserved_balance < withdrawal.amount:
                    messages.error(request, "Reserved balance is insufficient; withdrawal was not changed.")
                else:
                    withdrawal.status = "rejected"
                    withdrawal.rejection_reason = reason
                    withdrawal.save(update_fields=[
                        "status", "rejection_reason", "updated_at"
                    ])
                    earnings.reserved_balance -= withdrawal.amount
                    earnings.available_balance += withdrawal.amount
                    earnings.save(update_fields=[
                        "reserved_balance", "available_balance", "updated_at"
                    ])
                    messages.success(request, f"Withdrawal #{withdrawal.pk} rejected; funds restored.")
            else:
                messages.error(request, "This withdrawal cannot be changed using that action.")
        return redirect("base:admin_financial_dashboard")

    ledger_entries = (
        LedgerEntry.objects.select_related(
            "order", "order__restaurant", "order__user"
        )
        .order_by("-created_at")
    )
    totals = RestaurantEarnings.objects.aggregate(
        total_sales=Sum("total_eligible_sales"),
        total_commission=Sum("total_commission_deducted"),
        total_earnings=Sum("net_earnings"),
    )
    return render(request, "admin_financial_dashboard.html", {
        "total_sales": totals["total_sales"] or Decimal("0.00"),
        "total_commission": totals["total_commission"] or Decimal("0.00"),
        "total_earnings": totals["total_earnings"] or Decimal("0.00"),
        "withdrawals": WithdrawalRequest.objects.select_related(
            "restaurant", "restaurant__user"
        ).order_by("-created_at"),
        "ledgers": ledger_entries,
    })


@staff_only
def admin_ledger_detail(request, pk):
    entry = get_object_or_404(
        LedgerEntry.objects.select_related(
            "order", "order__user", "order__restaurant"
        ),
        pk=pk,
    )
    return render(request, "admin_ledger_detail.html", {
        "entry": entry,
        "order": entry.order,
    })


@staff_only
def admin_restaurant_wallets(request):
    wallets = RestaurantEarnings.objects.select_related(
        "restaurant", "restaurant__user"
    ).order_by("restaurant__restaurant_name")
    return render(request, "admin_restaurant_wallets.html", {"wallets": wallets})


@staff_only
def admin_commission_history(request):
    ledgers = (
        LedgerEntry.objects.filter(transaction_type="order_payment")
        .select_related("order", "order__restaurant", "order__user")
        .prefetch_related("order__items")
        .order_by("-created_at")
    )
    return render(request, "admin_commission_history.html", {"ledgers": ledgers})


@staff_only
def admin_orders(request):
    orders = (
        Order.objects.select_related("restaurant", "user", "delivery_partner")
        .prefetch_related("items", "ledger_entries")
        .order_by("-created_at")
    )
    return render(request, "dashboard/orders.html", {"orders": orders})


@staff_only
@require_POST
def admin_assign_delivery(request, pk):
    order = get_object_or_404(Order, pk=pk)
    partner = get_object_or_404(
        DeliveryPartnerProfile,
        pk=request.POST.get("delivery_partner_id"),
        status=DeliveryPartnerProfile.APPROVED,
    )
    order.delivery_partner = partner
    order.save(update_fields=["delivery_partner", "updated_at"])
    messages.success(request, f"Delivery partner assigned to order #{order.pk}.")
    return redirect("base:admin_orders")


# ---------- account profiles ----------
@restaurant_required
def restaurant_profile(request):
    return render(request, "restaurant/profile.html", {
        "profile": request.restaurant,
        "owner": request.user,
    })


@delivery_required
def delivery_profile(request):
    return render(request, "delivery/profile.html", {
        "profile": request.partner,
        "owner": request.user,
    })


@delivery_required
@require_POST
def delivery_update_location(request):
    if request.partner.status != DeliveryPartnerProfile.APPROVED:
        return JsonResponse({"detail": "Your account is not approved."}, status=403)
    try:
        coordinates = json.loads(request.body)
        latitude = Decimal(str(coordinates["lat"]))
        longitude = Decimal(str(coordinates["lng"]))
    except (ValueError, TypeError, KeyError, InvalidOperation):
        return JsonResponse({"detail": "Valid latitude and longitude are required."}, status=400)
    if (not latitude.is_finite() or not longitude.is_finite()
            or not Decimal("-90") <= latitude <= Decimal("90")
            or not Decimal("-180") <= longitude <= Decimal("180")):
        return JsonResponse({"detail": "Coordinates are outside the valid range."}, status=400)
    location, _ = DeliveryPartnerLocation.objects.update_or_create(
        partner=request.partner,
        defaults={"latitude": latitude, "longitude": longitude},
    )
    return JsonResponse({
        "lat": float(location.latitude),
        "lng": float(location.longitude),
        "updated_at": location.last_updated.isoformat(),
    })