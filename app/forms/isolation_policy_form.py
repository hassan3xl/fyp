from django import forms
from app.models.tenants import Tenant


class IsolationPolicyForm(forms.Form):
    isolation_mode = forms.ChoiceField(
        choices=[
            ('row', 'Row-level isolation'),
            ('schema', 'Schema-level isolation'),
            ('database', 'Database-level isolation'),
        ],
        label='Isolation Model',
        help_text='Select the tenant isolation model that suits the business workload.',
        initial='row',
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    tenant_name = forms.CharField(
        label='Tenant Name',
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    business_type = forms.ChoiceField(
        choices=Tenant.BUSINESS_TYPE_CHOICES,
        label='Business Type',
        required=False,
        disabled=True,
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    plan = forms.ChoiceField(
        choices=Tenant.PLAN_CHOICES,
        label='Pricing Plan',
        required=False,
        disabled=True,
        widget=forms.Select(attrs={'class': 'form-input'})
    )
