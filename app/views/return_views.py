import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.contrib import messages
from app.models import Product, Sale, SaleItem, ReturnTransaction, ReturnItem, ExchangeItem, TenantProfile, Tenant


def return_list(request, tenant_slug):
    """
    Displays the list of all return & exchange transactions for the current tenant.
    Supports searching by return ID, original sale ID, product name, or reason.
    """
    returns_qs = ReturnTransaction.objects.filter(
        tenant_id=request.tenant_id
    ).select_related('sale', 'user').prefetch_related(
        'returned_items__product',
        'exchange_items__product'
    ).order_by('-created_at')

    query = request.GET.get('q', '').strip()
    return_type_filter = request.GET.get('type', '').strip()

    if query:
        try:
            val_uuid = uuid.UUID(query)
            returns_qs = returns_qs.filter(models.Q(id=val_uuid) | models.Q(sale__id=val_uuid))
        except ValueError:
            returns_qs = returns_qs.filter(
                models.Q(id__icontains=query) |
                models.Q(sale__id__icontains=query) |
                models.Q(returned_items__product__name__icontains=query) |
                models.Q(exchange_items__product__name__icontains=query) |
                models.Q(reason_details__icontains=query)
            ).distinct()

    if return_type_filter and return_type_filter != 'all':
        returns_qs = returns_qs.filter(return_type=return_type_filter)

    return render(request, 'inventory/return_list.html', {
        'returns': returns_qs,
        'query': query,
        'return_type_filter': return_type_filter,
        'business_type': request.business_type,
    })


def return_detail(request, tenant_slug, pk):
    """
    Displays the detailed invoice / credit note / receipt for a specific return transaction.
    Supports printing thermal or standard A4 receipts.
    """
    return_tx = get_object_or_404(
        ReturnTransaction.objects.select_related('sale', 'user').prefetch_related(
            'returned_items__product',
            'returned_items__sale_item',
            'exchange_items__product'
        ),
        pk=pk,
        tenant_id=request.tenant_id
    )

    return render(request, 'inventory/return_detail.html', {
        'return_tx': return_tx,
        'sale': return_tx.sale,
        'returned_items': return_tx.returned_items.all(),
        'exchange_items': return_tx.exchange_items.all(),
        'business_type': request.business_type,
    })


def sale_lookup(request, tenant_slug):
    """
    Quick search endpoint for scanning or entering a receipt / sale ID.
    Directs to the sale details or return wizard.
    """
    query = request.GET.get('q', '').strip()
    action = request.GET.get('action', 'detail')  # 'detail' or 'return'

    if not query:
        return redirect('inventory:sale_list', tenant_slug=tenant_slug)

    # Try full UUID match
    try:
        val_uuid = uuid.UUID(query)
        sale = Sale.objects.filter(id=val_uuid, tenant_id=request.tenant_id).first()
        if sale:
            if action == 'return' and sale.can_return:
                return redirect('inventory:sale_return_new', tenant_slug=tenant_slug, pk=sale.id)
            return redirect('inventory:sale_detail', tenant_slug=tenant_slug, pk=sale.id)
    except ValueError:
        pass

    # Try partial ID match or product name query
    matching_sales = Sale.objects.filter(
        models.Q(id__icontains=query) |
        models.Q(items__product__name__icontains=query),
        tenant_id=request.tenant_id
    ).distinct()

    if matching_sales.count() == 1:
        sale = matching_sales.first()
        if action == 'return' and sale.can_return:
            return redirect('inventory:sale_return_new', tenant_slug=tenant_slug, pk=sale.id)
        return redirect('inventory:sale_detail', tenant_slug=tenant_slug, pk=sale.id)

    # If 0 or >1 matches, redirect to sale_list with search filter
    return redirect(f'/{tenant_slug}/sales/?q={query}')


def sale_return_new(request, tenant_slug, pk):
    """
    Handles returning products from an existing sale and optionally exchanging
    them for other products with atomic stock updates and financial delta calculation.
    """
    sale = get_object_or_404(Sale, pk=pk, tenant_id=request.tenant_id)
    error = None

    # Check if sale has any items eligible for return
    if not sale.can_return and request.method != 'POST':
        messages.warning(request, "All items in this sale have already been fully returned.")
        return redirect('inventory:sale_detail', tenant_slug=tenant_slug, pk=sale.id)

    if request.method == 'POST':
        return_type = request.POST.get('return_type', 'refund')
        reason = request.POST.get('reason', 'customer_request')
        reason_details = request.POST.get('reason_details', '').strip()

        # Parse return items from form
        # We expect inputs: return_sale_item_id[] and return_qty_<sale_item_id>, restock_<sale_item_id>
        sale_item_ids = request.POST.getlist('sale_item_ids')
        
        # Parse exchange items from form
        exchange_product_ids = request.POST.getlist('exchange_product_ids')
        exchange_quantities = request.POST.getlist('exchange_quantities')

        with transaction.atomic():
            return_items_to_create = []  # tuple of (sale_item, product, qty, unit_price, restock)
            products_to_restock = []     # (product, qty)
            return_subtotal = Decimal('0.00')

            # 1. Process Return Items
            for s_id in sale_item_ids:
                qty_str = request.POST.get(f'return_qty_{s_id}', '0').strip()
                restock_flag = request.POST.get(f'restock_{s_id}') == 'on'

                try:
                    qty = int(qty_str)
                except (ValueError, TypeError):
                    qty = 0

                if qty <= 0:
                    continue

                try:
                    sale_item = SaleItem.objects.select_for_update().get(
                        id=s_id,
                        sale=sale,
                        tenant_id=request.tenant_id
                    )
                except SaleItem.DoesNotExist:
                    error = "Invalid sale item selected."
                    break

                if qty > sale_item.remaining_quantity:
                    error = f"Cannot return {qty} units of '{sale_item.product.name}'. Max eligible for return: {sale_item.remaining_quantity}."
                    break

                item_refund_val = sale_item.unit_price * qty
                return_subtotal += item_refund_val

                return_items_to_create.append((sale_item, sale_item.product, qty, sale_item.unit_price, restock_flag))
                if restock_flag:
                    products_to_restock.append((sale_item.product, qty))

            if not error and not return_items_to_create:
                error = "Please specify at least one product and quantity to return."

            # 2. Process Exchange Items (if any)
            exchange_items_to_create = []  # tuple of (product, qty, unit_price)
            products_to_deduct = []        # (product, qty)
            exchange_subtotal = Decimal('0.00')

            if not error and (return_type == 'exchange' or exchange_product_ids):
                for p_id, eqty_str in zip(exchange_product_ids, exchange_quantities):
                    if not p_id or not eqty_str:
                        continue
                    try:
                        eqty = int(eqty_str)
                    except (ValueError, TypeError):
                        eqty = 0

                    if eqty <= 0:
                        continue

                    try:
                        ex_product = Product.objects.select_for_update().get(
                            id=p_id,
                            tenant_id=request.tenant_id
                        )
                    except Product.DoesNotExist:
                        error = "Selected exchange product does not exist."
                        break

                    # Check stock for replacement product
                    # Note: if the exchange product is the same product that is being restocked in this transaction,
                    # we should take the restocked units into account if restocked.
                    effective_available = ex_product.quantity
                    for r_prod, r_qty in products_to_restock:
                        if r_prod.id == ex_product.id:
                            effective_available += r_qty

                    if eqty > effective_available:
                        error = f"Insufficient stock for replacement product '{ex_product.name}'. Available: {ex_product.quantity}."
                        break

                    line_exchange_cost = ex_product.unit_price * eqty
                    exchange_subtotal += line_exchange_cost
                    exchange_items_to_create.append((ex_product, eqty, ex_product.unit_price))
                    products_to_deduct.append((ex_product, eqty))

            # Auto-set return_type if exchange items are present
            if exchange_items_to_create and return_type != 'exchange':
                return_type = 'exchange'

            if not error:
                # 3. Calculate Financial Balances
                net_adjustment = exchange_subtotal - return_subtotal
                if net_adjustment < Decimal('0.00'):
                    refund_amount = abs(net_adjustment)
                    additional_amount = Decimal('0.00')
                elif net_adjustment > Decimal('0.00'):
                    refund_amount = Decimal('0.00')
                    additional_amount = net_adjustment
                else:
                    refund_amount = Decimal('0.00')
                    additional_amount = Decimal('0.00')

                tenant = Tenant.objects.get(id=request.tenant_id)

                # 4. Create ReturnTransaction Record
                return_tx = ReturnTransaction.objects.create(
                    tenant=tenant,
                    sale=sale,
                    user=request.user,
                    return_type=return_type,
                    reason=reason,
                    reason_details=reason_details,
                    return_subtotal=return_subtotal,
                    exchange_subtotal=exchange_subtotal,
                    refund_amount=refund_amount,
                    additional_amount=additional_amount,
                    net_adjustment=net_adjustment,
                )

                # 5. Apply Inventory Restocking for Returned Items
                for prod, r_qty in products_to_restock:
                    prod.quantity += r_qty
                    prod.save()

                # 6. Apply Inventory Deductions for Replacement Items
                for prod, e_qty in products_to_deduct:
                    prod.quantity -= e_qty
                    prod.save()

                # 7. Create ReturnItem records
                for s_item, prod, qty, price, restock in return_items_to_create:
                    ReturnItem.objects.create(
                        tenant=tenant,
                        return_transaction=return_tx,
                        sale_item=s_item,
                        product=prod,
                        quantity=qty,
                        unit_price=price,
                        restocked=restock,
                    )

                # 8. Create ExchangeItem records
                for prod, qty, price in exchange_items_to_create:
                    ExchangeItem.objects.create(
                        tenant=tenant,
                        return_transaction=return_tx,
                        product=prod,
                        quantity=qty,
                        unit_price=price,
                    )

                return redirect('inventory:return_detail', tenant_slug=tenant_slug, pk=return_tx.id)

    # GET or Validation Error state
    sale_items = sale.items.all().select_related('product').prefetch_related('returns')
    available_products = Product.objects.filter(
        tenant_id=request.tenant_id,
        quantity__gt=0
    ).order_by('name')

    return render(request, 'inventory/sale_return_form.html', {
        'sale': sale,
        'sale_items': sale_items,
        'available_products': available_products,
        'error': error,
        'business_type': request.business_type,
    })
