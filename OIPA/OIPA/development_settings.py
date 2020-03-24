from OIPA.settings import *  # NOQA: F401, F403

MIDDLEWARE += [  # noqa: F405
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    'yet_another_django_profiler.middleware.ProfilerMiddleware'
]

INSTALLED_APPS += {  # noqa: F405
    # 'debug_toolbar',
    'yet_another_django_profiler'
}


def custom_show_toolbar(self):
    return True


SECRET_KEY = '__DEV_SECRET_KEY__'

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
}

# Don't cache anything when developing:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'api': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
}

# A setting indicating whether to save XML datasets (files) to local machine or
# not:
DOWNLOAD_DATASETS = False
