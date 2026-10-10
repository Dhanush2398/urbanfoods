from django.urls import path

from . import views

app_name = "base"

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.authView, name="authView"),
    path("login/", views.UrbanLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("restaurant/logout/", views.restaurant_logout, name="restaurant_logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("restaurant/signup/", views.restaurant_signup, name="restaurant_signup"),
    path("restaurant/login/", views.RestaurantLoginView.as_view(), name="restaurant_login"),
    path("restaurant/documents/", views.restaurant_documents, name="restaurant_documents"),
    path("restaurant/dashboard/", views.restaurant_dashboard, name="restaurant_dashboard"),
    path("dashboard/restaurants/", views.restaurant_requests, name="restaurant_requests"),
    path("dashboard/restaurants/<int:pk>/review/", views.restaurant_review, name="restaurant_review"),
    path("dashboard/restaurant-list/", views.restaurant_list, name="restaurant_list"),
    path("dashboard/restaurant-list/<int:pk>/", views.restaurant_detail, name="restaurant_detail"),
    path("restaurant/menu/", views.restaurant_menu, name="restaurant_menu"),
    path("restaurant/menu/<int:pk>/edit/", views.restaurant_menu, name="restaurant_menu_edit"),
    path("restaurant/menu/<int:pk>/delete/", views.restaurant_menu_delete, name="restaurant_menu_delete"),
    path("restaurant/<int:pk>/", views.restaurant_public, name="restaurant_public"),
    path("menu/<int:pk>/", views.menu_item_public, name="menu_item_public"),
    path("restaurant/<int:pk>/category/<str:category>/", views.restaurant_category, name="restaurant_category"),
    path("restaurants/", views.restaurant_directory, name="restaurants"),
    path("delivery/signup/", views.delivery_signup, name="delivery_signup"),
    path("delivery/login/", views.DeliveryLoginView.as_view(), name="delivery_login"),
    path("delivery/logout/", views.delivery_logout, name="delivery_logout"),
    path("delivery/documents/", views.delivery_documents, name="delivery_documents"),
    path("delivery/dashboard/", views.delivery_dashboard, name="delivery_dashboard"),
    path("dashboard/delivery-partners/",views.delivery_requests,name="delivery_requests",),
    path("dashboard/delivery-partners/<int:pk>/review/",views.delivery_review,name="delivery_review",),
    path("dashboard/delivery-partner-list/",views.delivery_list,name="delivery_list",),
    path("dashboard/delivery-partner-list/<int:pk>/",views.delivery_detail,name="delivery_detail",),
    path("restaurant/profile/",views.restaurant_profile,name="restaurant_profile",),
    path("delivery/profile/",views.delivery_profile,name="delivery_profile",),


]
