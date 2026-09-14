# see https://docs.djangoproject.com/en/stable/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications
import os
import sys
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
root = Path(__file__).resolve().parents[1].resolve()
kernel = Path(os.environ.get('KERNEL_CHECKOUT', root / '.deps' / 'django-trusts')).resolve()

cleaned = []
for p in sys.path:
    if '__editable__.django_trusts' in str(p):
        continue
    abs_p = Path(p or os.getcwd()).resolve()
    if abs_p in {root, kernel}:
        continue
    if (abs_p / 'trusts' / '__init__.py').is_file() and abs_p != kernel:
        continue
    cleaned.append(p)
sys.path[:] = cleaned
sys.meta_path[:] = [
    f for f in sys.meta_path
    if '__editable___django_trusts' not in getattr(f, '__module__', '')
]
sys.path_hooks[:] = [h for h in sys.path_hooks if '__editable___django_trusts' not in repr(h)]
if kernel.is_dir():
    sys.path.insert(0, str(kernel))
sys.path.append(str(root))

import django
from django.conf import settings
from django.test.utils import get_runner

NORMAL_SUITE = [
    'tests.test_packaging',
    'tests.test_facade',
    'tests.test_register',
    'tests.test_backend',
    'tests.test_fixed_query',
    'tests.test_issue100',
]


def runtests():
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=False)
    failures = test_runner.run_tests(sys.argv[1:] or NORMAL_SUITE)
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
