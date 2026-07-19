from django.urls import path
from app.views import (
    dashboard,
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
)

app_name = 'inventory'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('products/', product_list, name='product_list'),
    path('products/add/', product_add, name='product_add'),
    path('products/<uuid:pk>/edit/', product_edit, name='product_edit'),
    path('products/<uuid:pk>/delete/', product_delete, name='product_delete'),
    path('categories/', category_list, name='category_list'),
    path('categories/add/', category_add, name='category_add'),
    path('categories/<uuid:pk>/delete/', category_delete, name='category_delete'),
    path('sales/', sale_list, name='sale_list'),
    path('sales/new/', sale_new, name='sale_new'),
    path('sales/<uuid:pk>/', sale_detail, name='sale_detail'),
]
