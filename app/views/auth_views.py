from django.shortcuts import render, redirect
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from app.models.tenants import TenantProfile
from app.models.users import User, Profile
from app.forms.tenant_forms import RegistrationForm, LoginForm


def register_view(request):
    if request.user.is_authenticated:
        tenant = getattr(request.user, 'tenant', None)
        if tenant:
            if not tenant.is_onboarded:
                return redirect('/onboarding/')
            return redirect(f'/{tenant.slug}/')
        return redirect('/admin/')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            tenant = TenantProfile.objects.create(
                name=form.cleaned_data['business_name'],
                business_type=None,
                slug=form.cleaned_data['slug'],
                plan='standard',
                is_onboarded=False
            )

            full_name = form.cleaned_data['full_name']
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                tenant=tenant,
                role='tenant',
                first_name=first_name,
                last_name=last_name
            )

            Profile.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name
            )

            django_login(request, user)
            request.session['tenant_id'] = str(tenant.id)
            request.session['business_type'] = tenant.business_type
            request.session['plan'] = tenant.plan
            request.session['tenant_name'] = tenant.name

            return redirect('/onboarding/')
    else:
        form = RegistrationForm()

    return render(request, 'tenants/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        tenant = getattr(request.user, 'tenant', None)
        if tenant:
            if not tenant.is_onboarded:
                return redirect('/onboarding/')
            return redirect(f'/{tenant.slug}/')
        return redirect('/admin/')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            django_login(request, user)

            tenant = user.tenant
            if tenant:
                request.session['tenant_id'] = str(tenant.id)
                request.session['business_type'] = tenant.business_type
                request.session['plan'] = tenant.plan
                request.session['tenant_name'] = tenant.name
                
                if not tenant.is_onboarded:
                    return redirect('/onboarding/')
                return redirect(f'/{tenant.slug}/')
            else:
                request.session['tenant_id'] = None
                request.session['business_type'] = 'pharmacy'
                request.session['plan'] = 'standard'
                request.session['tenant_name'] = 'System Admin'
                return redirect('/admin/')
    else:
        form = LoginForm()

    return render(request, 'tenants/login.html', {'form': form})


def logout_view(request):
    django_logout(request)
    return redirect('/')


@login_required
def onboarding_view(request):
    tenant = getattr(request.user, 'tenant', None)
    if not tenant:
        return redirect('/admin/')
    
    if tenant.is_onboarded:
        return redirect(f'/{tenant.slug}/')

    if request.method == 'POST':
        business_type = request.POST.get('business_type')
        plan = request.POST.get('plan', 'standard')
        
        # Validate business_type
        valid_types = [t[0] for t in TenantProfile.BUSINESS_TYPE_CHOICES]
        if business_type in valid_types:
            tenant.business_type = business_type
            tenant.plan = plan
            tenant.is_onboarded = True
            tenant.save()

            request.session['business_type'] = tenant.business_type
            request.session['plan'] = tenant.plan
            
            return redirect(f'/{tenant.slug}/')

    business_types = [
        {
            'value': 'pharmacy',
            'label': 'Pharmacy / Drug Store',
            'desc': 'Track batch numbers, expiration dates, prescriptions, and manage medical inventory.',
            'icon': 'fa-prescription-bottle-alt'
        },
        {
            'value': 'provision_store',
            'label': 'Provision / Retail Store',
            'desc': 'Perfect for daily items, packaged goods, quick retail checkouts, and custom categories.',
            'icon': 'fa-shopping-basket'
        },
        {
            'value': 'supermarket',
            'label': 'Supermarket / Grocery Store',
            'desc': 'Manage high-volume retail transactions, barcode scanning, categories, and multiple cashiers.',
            'icon': 'fa-store'
        },
        {
            'value': 'electronic_store',
            'label': 'Electronics & Tech Shop',
            'desc': 'Track serial numbers, hardware models, technical inventory details, and product warranties.',
            'icon': 'fa-laptop'
        }
    ]

    context = {
        'business_types': business_types,
        'plans': [
            {'value': 'standard', 'label': 'Standard Plan', 'desc': 'Up to 100 API requests/min. Perfect for growing shops.', 'badge': 'Popular'},
            {'value': 'premium', 'label': 'Premium Plan', 'desc': 'Up to 300 API requests/min, priority support, and advanced analytics.', 'badge': 'Enterprise'}
        ]
    }
    return render(request, 'tenants/onboarding.html', context)
