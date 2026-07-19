from django.contrib import admin
from app.models import Category, Product, Sale, SaleItem, TenantProfile, User

admin.site.register(TenantProfile)
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(SaleItem)
