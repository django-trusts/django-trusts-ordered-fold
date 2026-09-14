import os

SECRET_KEY = '01)%8q7ub=+yw7^#dz5s!6kkff6%al5f)_ayvep9_b&w1q-dvs'

USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
ALLOWED_HOSTS = ['testserver', 'localhost']

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'tests.apps.TestsConfig',
    'tests.fold_host.apps.FoldHostConfig',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend',
)

if os.environ.get('TRUSTS_TEST_DATABASE') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('TRUSTS_PG_NAME', 'trusts'),
            'USER': os.environ.get('TRUSTS_PG_USER', 'postgres'),
            'PASSWORD': os.environ.get('TRUSTS_PG_PASSWORD', 'postgres'),
            'HOST': os.environ.get('TRUSTS_PG_HOST', '127.0.0.1'),
            'PORT': os.environ.get('TRUSTS_PG_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

ROOT_URLCONF = 'tests.urls'
