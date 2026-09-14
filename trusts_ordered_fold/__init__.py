"""PostgreSQL ordered allow/deny authorization backend for django-trusts.

Import root is ``trusts_ordered_fold``, not ``trusts.ordered_fold``.
This package owns the OrderedFold engine and the concrete
``TrustsOrderedFoldModelBackend``. Core C2 deleted the provisional
shims; do not import ``trusts.ordered_fold``.

Importing this module registers system check ``trusts_ordered_fold.E001``.
"""

from trusts_ordered_fold.apps import OrderedFoldImplementationConfig
from trusts_ordered_fold.engine import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
)
from trusts_ordered_fold.registry import (
    OrderedFoldBackendHandle,
    OrderedFoldQueryCompiler,
    OrderedFoldRegistry,
    register_ordered_fold,
)

# Unavoidable vendor check: package import registers E001.
from trusts_ordered_fold import checks as _checks  # noqa: F401

for _exported in (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
):
    _exported.__module__ = 'trusts_ordered_fold'
del _exported

__all__ = (
    'AuthorizedManager',
    'AuthorizedQuerySet',
    'FlatToken',
    'MaskEntry',
    'OrderedFold',
    'OrderedFoldBackendHandle',
    'OrderedFoldImplementationConfig',
    'OrderedFoldQueryCompiler',
    'OrderedFoldRegistry',
    'PermissionMaskDomain',
    'PolarityMap',
    'TrustsOrderedFoldModelBackend',
    'authorization_required',
    'common_permissions',
    'granted',
    'register_ordered_fold',
)


def __getattr__(name):
    # Lazy: ModelBackend / auth.Permission imports are unsafe while
    # Django is still constructing AppConfigs.
    if name == 'TrustsOrderedFoldModelBackend':
        from trusts_ordered_fold.backends import TrustsOrderedFoldModelBackend
        return TrustsOrderedFoldModelBackend
    if name == 'authorization_required':
        from trusts_ordered_fold.decorators import authorization_required
        return authorization_required
    if name in {
        'AuthorizedManager',
        'AuthorizedQuerySet',
        'common_permissions',
        'granted',
    }:
        from trusts_ordered_fold import query as _query
        return getattr(_query, name)
    raise AttributeError('module %r has no attribute %r' % (__name__, name))
