"""
Root URLconf.

Every app gets its own include with a namespace. Routes are grouped by who they are for rather
than by what they act on, so an entry sitting in the wrong group is visible here without opening
the view. See docs/url-design.md.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Moved off the default /admin/ so the path everyone probes returns a 404.
    path('servicehub-admin/', admin.site.urls),

    path('accounts/', include('accounts.urls')),
    path('services/', include('services.urls')),
    path('', include('core.urls')),
]
