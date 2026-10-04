from .auth_views import login_view, logout_view, register_view
from .dashboard_views import dashboard
from .product_views import (
    product_list,
    product_add,
    product_edit,
    product_delete,
    category_list,
    category_add,
    category_delete,
    sale_list,
    sale_new,
    sale_detail,
    sale_pdf,
)
from .return_views import (
    return_list,
    return_detail,
    return_pdf,
    sale_return_new,
    sale_lookup,
)

__all__ = [
    'login_view',
    'logout_view',
    'register_view',
    'dashboard',
    'product_list',
    'product_add',
    'product_edit',
    'product_delete',
    'category_list',
    'category_add',
    'category_delete',
    'sale_list',
    'sale_new',
    'sale_detail',
    'sale_pdf',
    'return_list',
    'return_detail',
    'return_pdf',
    'sale_return_new',
    'sale_lookup',
]

