"""
Root URL configuration.

Paths are grouped by who they are for rather than by what they act on. Everything under
/manage/ is administrator-only and everything under /staff/ is for cleaners, so a URL that ends
up in the wrong group is obvious to a reviewer without reading the view.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Moved off the default /admin/ path. Not security on its own, but it keeps the site out of
    # the way of the scanners that only ever try /admin/.
    path('servicehub-admin/', admin.site.urls),

    path('accounts/', include('accounts.urls')),
    path('services/', include('services.urls')),
    path('bookings/', include('bookings.urls')),
    path('staff/', include('bookings.staff_urls')),
    path('manage/', include('core.manage_urls')),
    path('', include('core.urls')),
]
