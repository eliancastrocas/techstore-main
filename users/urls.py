from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("home/", views.home, name="home"),
    path("edit-profile/", views.edit_profile, name="edit_profile"),
    path("contact/", views.contact, name="contact"),
    
    # Vendor registration
    path("vendor/register/", views.vendor_register, name="vendor_register"),

    path("vendor/dashboard/", views.vendor_dashboard, name="vendor_dashboard"),
    path("vendor/movimientos/", views.vendor_movimientos, name="vendor_movimientos"),
    path("vendor/movimientos/pdf/", views.vendor_movimientos_pdf, name="vendor_movimientos_pdf"),
    
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    # Admin vendor management
    path("admin/vendors/", views.admin_vendors, name="admin_vendors"), 
    path("admin/vendors/approve/<int:profile_id>/", views.approve_vendor, name="approve_vendor"),
    path("admin/vendors/reject/<int:profile_id>/", views.reject_vendor, name="reject_vendor"),
    path("admin/vendors/toggle/<int:profile_id>/", views.toggle_vendor_status, name="toggle_vendor_status"),
    path("admin/vendors/resend/<int:profile_id>/", views.vendor_resend_code, name="vendor_resend_code"),
    
    # Admin user management (all users)
    path("admin/users/approve/<int:profile_id>/", views.admin_approve_user, name="admin_approve_user"),
    path("admin/users/toggle-role/<int:profile_id>/", views.admin_toggle_role, name="admin_toggle_role"),
    path("admin/users/toggle/<int:profile_id>/", views.admin_toggle_status, name="admin_toggle_status"),
    path("admin/users/delete/<int:profile_id>/", views.admin_delete_user, name="admin_delete_user"),
    path("admin/users/detail/<int:profile_id>/", views.admin_user_detail, name="admin_user_detail"),
]
