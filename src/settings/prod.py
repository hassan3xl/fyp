from decouple import config
import dj_database_url
from .base import *

DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

DATABASES = {
    'default': dj_database_url.parse(config('DATABASE_URL'),
    conn_max_age=0
    )
}

DATABASES['default']['CONN_MAX_AGE'] = 600

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'prod-cache',
    }
}
