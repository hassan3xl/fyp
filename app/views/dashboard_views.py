from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from app.models import Category, Product, Sale, SaleItem
from app.forms import CategoryForm, ProductForm, LoginForm, RegistrationForm
from app.models import TenantProfile, User

def dashboard(request, tenant_slug):
    total_products = Product.objects.filter(tenant_id=request.tenant_id).count()
    total_categories = Category.objects.filter(tenant_id=request.tenant_id).count()

    business_type = request.business_type

    if business_type == 'provision_store':
        low_stock_count = Product.objects.filter(
            reorder_level__isnull=False,
            quantity__lte=models.F('reorder_level')
        ).count()
    else:
        low_stock_count = Product.objects.filter(quantity__lte=5).count()

    recent_sales = Sale.objects.order_by('-created_at')[:5]

    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'low_stock_count': low_stock_count,
        'recent_sales': recent_sales,
    }
    return render(request, 'inventory/dashboard.html', context)
