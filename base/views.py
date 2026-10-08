from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import Http404
from django.db.models import Count, Q
from .forms import (
    DeliveryLoginForm, PhoneLoginForm, RegistrationForm, RestaurantRegistrationForm,
    RestaurantDocumentForm, RestaurantLoginForm, MenuItemForm, DeliveryRegistrationForm, DeliveryDocumentForm, DeliveryLoginForm
)
from .models import RestaurantProfile, MenuItem,CATEGORY_CHOICES,DeliveryPartnerProfile
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
    return render(request, "profile.html")


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
    return render(request, "restaurant/dashboard.html", {
        "profile": request.restaurant,
        "menu_count": request.restaurant.menu_items.count(),
    })


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
    veg = request.GET.get("veg") == "1"
    sort = request.GET.get("sort", "new")

    qs = RestaurantProfile.objects.filter(status=RestaurantProfile.APPROVED).annotate(
        item_count=Count("menu_items", filter=Q(menu_items__is_available=True), distinct=True),
        nonveg_count=Count("menu_items", filter=Q(menu_items__is_available=True,
                                                  menu_items__is_veg=False), distinct=True),
    )

    if q:
        by_item = MenuItem.objects.filter(is_available=True, name__icontains=q).values("restaurant_id")
        qs = qs.filter(Q(restaurant_name__icontains=q) | Q(city__icontains=q) | Q(pk__in=by_item))

    if selected:
        cq = Q()
        for c in selected:
            cq |= Q(category_names__icontains=c)
        qs = qs.filter(pk__in=MenuItem.objects.filter(is_available=True).filter(cq).values("restaurant_id"))

    if veg:
        qs = qs.filter(item_count__gt=0, nonveg_count=0)

    qs = qs.order_by({"name": "restaurant_name", "items": "-item_count"}.get(sort, "-created_at"))

    page_obj = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "restaurants.html", {
        "page_obj": page_obj,
        "q": q, "veg": veg, "sort": sort,
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

    return render(
        request,
        "delivery/dashboard.html",
        {
            "profile": profile
        }
    )
    
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