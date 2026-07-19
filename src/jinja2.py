from jinja2 import Environment, pass_context
from django.urls import reverse
from django.templatetags.static import static

@pass_context
def custom_reverse(context, viewname, *args, **kwargs):
    request = context.get('request')
    if request:
        resolver_match = getattr(request, 'resolver_match', None)
        tenant_slug = None
        if resolver_match:
            tenant_slug = resolver_match.kwargs.get('tenant_slug')
        if not tenant_slug and hasattr(request, 'tenant_slug'):
            tenant_slug = request.tenant_slug

        if tenant_slug and viewname.startswith('inventory:'):
            if 'kwargs' not in kwargs:
                kwargs['kwargs'] = {}
            kwargs['kwargs']['tenant_slug'] = tenant_slug

    return reverse(viewname, args=args, **kwargs)

def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': custom_reverse,
    })
    return env
