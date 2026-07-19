from django.urls import include, path

urlpatterns = [
    path('', include('app.urls.tenant_urls')),
]
