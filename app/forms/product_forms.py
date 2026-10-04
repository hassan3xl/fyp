from django import forms
from app.models import Category, Product

FORM_INPUT_CLASS = (
    'w-full text-xs sm:text-sm py-2.5 px-3.5 border border-slate-300 rounded-xl '
    'bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 '
    'focus:ring-emerald-500/20 focus:border-emerald-600 transition-all'
)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': FORM_INPUT_CLASS, 'rows': 3, 'placeholder': 'Category Description'}),
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
            'category': forms.Select(attrs={'class': FORM_INPUT_CLASS}),
            'name': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'Product Name'}),
            'sku': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'e.g. 890123456789 or PRD-001'}),
            'quantity': forms.NumberInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': '0', 'min': '0'}),
            'unit_price': forms.NumberInput(attrs={'class': FORM_INPUT_CLASS, 'step': '0.01', 'placeholder': '0.00', 'min': '0'}),

            # Pharmacy
            'batch_number': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'Batch Number'}),
            'manufacturer': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'Manufacturer'}),
            'expiry_date': forms.DateInput(attrs={'class': FORM_INPUT_CLASS, 'type': 'date'}),
            'nafdac_number': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'NAFDAC Number'}),

            # Provision Store
            'reorder_level': forms.NumberInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'Reorder Level', 'min': '0'}),
            'supplier_code': forms.TextInput(attrs={'class': FORM_INPUT_CLASS, 'placeholder': 'Supplier Code'}),
        }
        labels = {
            'sku': 'Product Code / SKU',
        }

    def __init__(self, *args, **kwargs):
        business_type = kwargs.pop('business_type', 'pharmacy')
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['category'].queryset = Category.objects.filter(tenant_id=tenant_id)
        else:
            self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].empty_label = "Select a Category"
        self.fields['sku'].label = 'Product Code / SKU'

        # Dynamically set required attributes
        if business_type == 'pharmacy':
            self.fields['reorder_level'].required = False
            self.fields['supplier_code'].required = False
        else:
            self.fields['batch_number'].required = False
            self.fields['manufacturer'].required = False
            self.fields['expiry_date'].required = False
            self.fields['nafdac_number'].required = False
