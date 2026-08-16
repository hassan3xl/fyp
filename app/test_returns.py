from decimal import Decimal
from django.test import TestCase, Client
from app.models import TenantProfile, Tenant, User, Category, Product, Sale, SaleItem, ReturnTransaction, ReturnItem, ExchangeItem


class ProductReturnWorkflowTests(TestCase):
    def setUp(self):
        # 1. Create Tenant Profile & User
        self.tenant = TenantProfile.objects.create(
            name="Apex Pharmacy & Mart",
            slug="apex",
            business_type="pharmacy",
            plan="premium",
            is_onboarded=True
        )

        self.user = User.objects.create_user(
            email="pharmacist@apex.com",
            password="password123",
            tenant_id=self.tenant.id,
            first_name="Jane",
            last_name="Doe",
            role="admin"
        )


        self.client = Client()
        # Log in the user
        self.client.login(email="pharmacist@apex.com", password="password123")

        # 2. Create Categories & Products
        self.category = Category.objects.create(
            tenant_id=self.tenant.id,
            name="Analgesics"
        )

        self.product_a = Product.objects.create(
            tenant_id=self.tenant.id,
            category=self.category,
            name="Paracetamol 500mg",
            sku="PARA-500",
            unit_price=Decimal("100.00"),
            quantity=10,
            batch_number="BATCH-001"
        )

        self.product_b = Product.objects.create(
            tenant_id=self.tenant.id,
            category=self.category,
            name="Ibuprofen 400mg",
            sku="IBU-400",
            unit_price=Decimal("150.00"),
            quantity=10,
            batch_number="BATCH-002"
        )

        # 3. Create a Sale: 4 units of Product A
        self.sale = Sale.objects.create(
            tenant=self.tenant,
            user=self.user,
            total_amount=Decimal("400.00")
        )
        self.sale_item_a = SaleItem.objects.create(
            tenant=self.tenant,
            sale=self.sale,
            product=self.product_a,
            quantity=4,
            unit_price=Decimal("100.00")
        )
        self.product_a.quantity = 6
        self.product_a.save()

    def test_initial_sale_state(self):
        self.assertEqual(self.sale.status, 'completed')
        self.assertTrue(self.sale.can_return)
        self.assertEqual(self.sale_item_a.remaining_quantity, 4)
        self.assertEqual(self.sale_item_a.returned_quantity, 0)
        self.assertEqual(self.sale.net_total, Decimal("400.00"))

    def test_return_refund_with_inventory_restocking(self):
        """Returning 2 units with restock restores inventory and calculates refund accurately."""
        url = f"/{self.tenant.slug}/sales/{self.sale.id}/return/"
        post_data = {
            'return_type': 'refund',
            'reason': 'customer_request',
            'reason_details': 'Customer bought excess packs',
            'sale_item_ids': [str(self.sale_item_a.id)],
            f'return_qty_{self.sale_item_a.id}': '2',
            f'restock_{self.sale_item_a.id}': 'on',
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        # Verify ReturnTransaction
        self.assertEqual(ReturnTransaction.objects.count(), 1)
        return_tx = ReturnTransaction.objects.first()
        self.assertEqual(return_tx.sale, self.sale)
        self.assertEqual(return_tx.return_type, 'refund')
        self.assertEqual(return_tx.return_subtotal, Decimal("200.00"))
        self.assertEqual(return_tx.refund_amount, Decimal("200.00"))
        self.assertEqual(return_tx.additional_amount, Decimal("0.00"))

        # Verify ReturnItem
        self.assertEqual(return_tx.returned_items.count(), 1)
        ret_item = return_tx.returned_items.first()
        self.assertEqual(ret_item.quantity, 2)
        self.assertTrue(ret_item.restocked)
        self.assertEqual(ret_item.total_refund_value, Decimal("200.00"))

        # Verify Stock Level (6 + 2 = 8)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.quantity, 8)

        # Verify Sale & SaleItem remaining state
        self.sale_item_a.refresh_from_db()
        self.assertEqual(self.sale_item_a.returned_quantity, 2)
        self.assertEqual(self.sale_item_a.remaining_quantity, 2)
        self.assertTrue(self.sale_item_a.can_return)

        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, 'partially_returned')
        self.assertEqual(self.sale.net_total, Decimal("200.00"))

    def test_return_without_restock_damaged_goods(self):
        """Damaged items returned without restock do not increase product stock level."""
        url = f"/{self.tenant.slug}/sales/{self.sale.id}/return/"
        post_data = {
            'return_type': 'refund',
            'reason': 'damaged',
            'reason_details': 'Seal broken, discard product',
            'sale_item_ids': [str(self.sale_item_a.id)],
            f'return_qty_{self.sale_item_a.id}': '1',
            # restock checkbox omitted -> False
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        return_tx = ReturnTransaction.objects.first()
        ret_item = return_tx.returned_items.first()
        self.assertFalse(ret_item.restocked)

        # Stock should remain at 6
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.quantity, 6)

    def test_product_exchange_with_refund_delta(self):
        """
        Exchange 2 units of Product A (₦200.00 value) for 1 unit of Product B (₦150.00 value).
        Store should refund customer ₦50.00 difference.
        Product A stock increases by 2, Product B stock decreases by 1.
        """
        url = f"/{self.tenant.slug}/sales/{self.sale.id}/return/"
        post_data = {
            'return_type': 'exchange',
            'reason': 'wrong_item',
            'reason_details': 'Patient required Ibuprofen instead',
            'sale_item_ids': [str(self.sale_item_a.id)],
            f'return_qty_{self.sale_item_a.id}': '2',
            f'restock_{self.sale_item_a.id}': 'on',
            'exchange_product_ids': [str(self.product_b.id)],
            'exchange_quantities': ['1'],
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        return_tx = ReturnTransaction.objects.first()
        self.assertEqual(return_tx.return_type, 'exchange')
        self.assertEqual(return_tx.return_subtotal, Decimal("200.00"))
        self.assertEqual(return_tx.exchange_subtotal, Decimal("150.00"))
        self.assertEqual(return_tx.refund_amount, Decimal("50.00"))
        self.assertEqual(return_tx.additional_amount, Decimal("0.00"))

        # Check stock updates
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.quantity, 8)  # 6 + 2

        self.product_b.refresh_from_db()
        self.assertEqual(self.product_b.quantity, 9)  # 10 - 1

        # Check ExchangeItem
        self.assertEqual(return_tx.exchange_items.count(), 1)
        ex_item = return_tx.exchange_items.first()
        self.assertEqual(ex_item.product, self.product_b)
        self.assertEqual(ex_item.quantity, 1)
        self.assertEqual(ex_item.unit_price, Decimal("150.00"))

        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, 'exchanged')

    def test_product_exchange_with_additional_customer_payment(self):
        """
        Exchange 1 unit of Product A (₦100.00) for 1 unit of Product B (₦150.00).
        Customer pays additional ₦50.00.
        """
        url = f"/{self.tenant.slug}/sales/{self.sale.id}/return/"
        post_data = {
            'return_type': 'exchange',
            'reason': 'wrong_item',
            'sale_item_ids': [str(self.sale_item_a.id)],
            f'return_qty_{self.sale_item_a.id}': '1',
            f'restock_{self.sale_item_a.id}': 'on',
            'exchange_product_ids': [str(self.product_b.id)],
            'exchange_quantities': ['1'],
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        return_tx = ReturnTransaction.objects.first()
        self.assertEqual(return_tx.return_type, 'exchange')
        self.assertEqual(return_tx.return_subtotal, Decimal("100.00"))
        self.assertEqual(return_tx.exchange_subtotal, Decimal("150.00"))
        self.assertEqual(return_tx.refund_amount, Decimal("0.00"))
        self.assertEqual(return_tx.additional_amount, Decimal("50.00"))

        self.sale.refresh_from_db()
        self.assertEqual(self.sale.net_total, Decimal("450.00"))  # 400 - 0 + 50

    def test_return_quantity_cannot_exceed_purchased_quantity(self):
        """Returns exceeding the purchased or remaining quantity are rejected with an error."""
        url = f"/{self.tenant.slug}/sales/{self.sale.id}/return/"
        post_data = {
            'return_type': 'refund',
            'sale_item_ids': [str(self.sale_item_a.id)],
            f'return_qty_{self.sale_item_a.id}': '10',  # Only 4 purchased
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot return 10 units")
        self.assertEqual(ReturnTransaction.objects.count(), 0)

    def test_full_return_updates_status_to_returned(self):
        """Returning all 4 units marks the sale as fully returned and disables further returns."""
        url = f"/{self.tenant.slug}/sales/{self.sale.id}/return/"
        post_data = {
            'return_type': 'refund',
            'sale_item_ids': [str(self.sale_item_a.id)],
            f'return_qty_{self.sale_item_a.id}': '4',
            f'restock_{self.sale_item_a.id}': 'on',
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, 'returned')
        self.assertFalse(self.sale.can_return)
        self.assertEqual(self.sale.net_total, Decimal("0.00"))

    def test_sale_lookup_and_redirection(self):
        """Testing lookup by exact UUID and query."""
        # 1. Exact UUID lookup with action=return
        lookup_url = f"/{self.tenant.slug}/sales/lookup/?q={self.sale.id}&action=return"
        resp = self.client.get(lookup_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/{self.tenant.slug}/sales/{self.sale.id}/return/", resp.url)

        # 2. Lookup with action=detail
        lookup_url = f"/{self.tenant.slug}/sales/lookup/?q={self.sale.id}&action=detail"
        resp = self.client.get(lookup_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/{self.tenant.slug}/sales/{self.sale.id}/", resp.url)

    def test_multi_tenant_isolation_on_returns(self):
        """Tenant B cannot view, lookup, or return a sale belonging to Tenant A."""
        # Create Tenant B
        tenant_b = TenantProfile.objects.create(
            name="Beta Pharmacy",
            slug="beta",
            business_type="pharmacy",
            plan="standard",
            is_onboarded=True
        )
        User.objects.create_user(
            email="user@beta.com",
            password="password123",
            tenant_id=tenant_b.id
        )

        client_b = Client()
        client_b.login(email="user@beta.com", password="password123")

        # Attempt to access Tenant A's sale return page from Tenant B's session
        url = f"/beta/sales/{self.sale.id}/return/"
        resp = client_b.get(url)
        self.assertEqual(resp.status_code, 404)

