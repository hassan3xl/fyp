from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls.auth_urls')),
    path('<slug:tenant_slug>/', include('app.urls')),
]
