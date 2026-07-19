from django import forms
from app.models import Category, Product

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Category Description'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category', 'name', 'sku', 'quantity', 'unit_price',
            'batch_number', 'manufacturer', 'expiry_date', 'nafdac_number',
            'reorder_level', 'supplier_code'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Product Name'}),
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'SKU'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),

            # Pharmacy
            'batch_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Batch Number'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Manufacturer'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'nafdac_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'NAFDAC Number'}),

            # Provision Store
            'reorder_level': forms.NumberInput(attrs={'class': 'form-input'}),
            'supplier_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Supplier Code'}),
        }

    def __init__(self, *args, **kwargs):
        business_type = kwargs.pop('business_type', 'pharmacy')
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].empty_label = "Select a Category"

        # Dynamically set required attributes
        if business_type == 'pharmacy':
            self.fields['reorder_level'].required = False
            self.fields['supplier_code'].required = False
        else:
            self.fields['batch_number'].required = False
            self.fields['manufacturer'].required = False
            self.fields['expiry_date'].required = False
            self.fields['nafdac_number'].required = False
