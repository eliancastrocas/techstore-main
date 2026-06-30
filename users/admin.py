from django.contrib import admin

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# Register UserProfile
admin.site.register(UserProfile)

# Make built-in User editable (optional, for completeness)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

from .models import Complaint
admin.site.register(Complaint)
