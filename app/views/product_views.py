import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.contrib.auth.decorators import login_required
from app.models import Category, Product, Sale, SaleItem, ReturnTransaction, ReturnItem, ExchangeItem
from app.forms import CategoryForm, ProductForm
from app.models import TenantProfile, User, Tenant


def product_list(request, tenant_slug):
    products = Product.objects.filter(tenant_id=request.tenant_id).select_related('category')
    return render(request, 'inventory/product_list.html', {
        'products': products,
        'business_type': request.business_type
    })

def product_add(request, tenant_slug):
    if request.method == 'POST':
        form = ProductForm(request.POST, business_type=request.business_type)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant_id = request.tenant_id
            product.save()
            return redirect('inventory:product_list', tenant_slug=tenant_slug)
    else:
        form = ProductForm(business_type=request.business_type)
    return render(request, 'inventory/product_form.html', {'form': form, 'action': 'Add'})

def product_edit(request, tenant_slug, pk):
    product = get_object_or_404(Product, pk=pk, tenant_id=request.tenant_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product, business_type=request.business_type)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant_id = request.tenant_id
            product.save()
            return redirect('inventory:product_list', tenant_slug=tenant_slug)
    else:
        form = ProductForm(instance=product, business_type=request.business_type)
    return render(request, 'inventory/product_form.html', {'form': form, 'action': 'Edit', 'product': product})

def product_delete(request, tenant_slug, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk, tenant_id=request.tenant_id)
        product.delete()
    return redirect('inventory:product_list', tenant_slug=tenant_slug)

def category_list(request, tenant_slug):
    categories = Category.objects.filter(tenant_id=request.tenant_id)
    return render(request, 'inventory/category_list.html', {'categories': categories})

def category_add(request, tenant_slug):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.tenant_id = request.tenant_id
            category.save()
            return redirect('inventory:category_list', tenant_slug=tenant_slug)
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form})

def category_delete(request, tenant_slug, pk):
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=pk, tenant_id=request.tenant_id)
        category.delete()
    return redirect('inventory:category_list', tenant_slug=tenant_slug)

def sale_list(request, tenant_slug):
    sales_qs = Sale.objects.filter(
        tenant_id=request.tenant_id
    ).select_related('user').prefetch_related(
        'items__product',
        'returns__returned_items',
        'returns__exchange_items'
    ).order_by('-created_at')

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if query:
        try:
            val_uuid = uuid.UUID(query)
            sales_qs = sales_qs.filter(id=val_uuid)
        except ValueError:
            sales_qs = sales_qs.filter(
                models.Q(id__icontains=query) |
                models.Q(items__product__name__icontains=query) |
                models.Q(user__email__icontains=query)
            ).distinct()

    sales = list(sales_qs)
    if status_filter and status_filter != 'all':
        sales = [s for s in sales if s.status == status_filter]

    return render(request, 'inventory/sale_list.html', {
        'sales': sales,
        'query': query,
        'status_filter': status_filter,
        'business_type': request.business_type
    })

def sale_new(request, tenant_slug):
    error = None
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        quantities = request.POST.getlist('quantities')

        with transaction.atomic():
            total_amount = 0
            sale_items_to_create = []
            products_to_update = []

            for pid, qty_str in zip(product_ids, quantities):
                if not pid or not qty_str:
                    continue
                try:
                    qty = int(qty_str)
                    if qty <= 0:
                        continue
                except ValueError:
                    continue

                try:
                    product = Product.objects.get(id=pid, tenant_id=request.tenant_id)
                except Product.DoesNotExist:
                    continue

                if product.quantity < qty:
                    error = f"Not enough stock for {product.name}. Available: {product.quantity}."
                    break

                item_total = product.unit_price * qty
                total_amount += item_total

                product.quantity -= qty
                products_to_update.append(product)
                sale_items_to_create.append((product, qty, product.unit_price))

            if not error and not sale_items_to_create:
                error = "Please select at least one product with a valid quantity."

            if not error:
                tenant = Tenant.objects.get(id=request.tenant_id)
                sale = Sale.objects.create(
                    tenant=tenant,
                    user=request.user,
                    total_amount=total_amount
                )

                for prod in products_to_update:
                    prod.save()

                for prod, qty, price in sale_items_to_create:
                    SaleItem.objects.create(
                        tenant=tenant,
                        sale=sale,
                        product=prod,
                        quantity=qty,
                        unit_price=price
                    )

                return redirect('inventory:sale_list', tenant_slug=tenant_slug)

    products = Product.objects.filter(tenant_id=request.tenant_id, quantity__gt=0)
    return render(request, 'inventory/sale_new.html', {
        'products': products,
        'error': error
    })

def sale_detail(request, tenant_slug, pk):
    sale = get_object_or_404(Sale, pk=pk, tenant_id=request.tenant_id)
    items = sale.items.all().select_related('product').prefetch_related('returns')
    returns = sale.returns.all().select_related('user').prefetch_related(
        'returned_items__product',
        'exchange_items__product'
    ).order_by('-created_at')
    return render(request, 'inventory/sale_detail.html', {
        'sale': sale,
        'items': items,
        'returns': returns,
        'business_type': request.business_type
    })


