#!/usr/bin/env python3
"""Install the wheel outside the checkout and import the six public names."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    wheels = sorted((ROOT / 'dist').glob('django_trusts_ordered_fold-*.whl'))
    if not wheels:
        raise SystemExit('no wheel in dist/')
    work = Path(os.environ.get('VERIFY_WORKDIR') or '').resolve() if os.environ.get('VERIFY_WORKDIR') else Path(os.getcwd())
    env = os.environ.copy()
    env['PYTHONPATH'] = ''
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', str(wheels[-1])],
        env=env,
    )
    script = r"""
import django
from django.conf import settings
settings.configure(
    INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
    SECRET_KEY='verify-wheel',
    USE_TZ=True,
    DEFAULT_AUTO_FIELD='django.db.models.AutoField',
)
django.setup()
from trusts.core import (
    FlatToken as CoreFlatToken,
    MaskEntry as CoreMaskEntry,
    OrderedFold as CoreOrderedFold,
    PermissionMaskDomain as CorePermissionMaskDomain,
    PolarityMap as CorePolarityMap,
)
from trusts_ordered_fold import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
    register_ordered_fold,
)
assert OrderedFold is CoreOrderedFold
assert PermissionMaskDomain is CorePermissionMaskDomain
assert MaskEntry is CoreMaskEntry
assert PolarityMap is CorePolarityMap
assert FlatToken is CoreFlatToken
assert callable(register_ordered_fold)
print('wheel import ok')
"""
    subprocess.check_call(
        [sys.executable, '-c', script],
        cwd=str(work),
        env=env,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
