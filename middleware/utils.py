import threading

_thread_locals = threading.local()


def get_current_tenant_id():
    return getattr(_thread_locals, 'tenant_id', None)


def set_current_tenant_id(tenant_id):
    _thread_locals.tenant_id = tenant_id


def clear_current_tenant():
    if hasattr(_thread_locals, 'tenant_id'):
        del _thread_locals.tenant_id
