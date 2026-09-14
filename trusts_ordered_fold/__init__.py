"""Provisional OrderedFold façade over django-trusts Core.

Import root is ``trusts_ordered_fold``, not ``trusts.ordered_fold``.
P1 re-exports Core's current construction types and forwards
``register_ordered_fold`` to ``BackendHandle.register_ordered_fold``.
The engine remains in Core until P2, which will own it and add
``TrustsOrderedFoldModelBackend``.
"""

from trusts.core import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
)

__all__ = (
    'FlatToken',
    'MaskEntry',
    'OrderedFold',
    'PermissionMaskDomain',
    'PolarityMap',
    'register_ordered_fold',
)


def register_ordered_fold(backend, source, fold):
    """Donate one OrderedFold plan through the extension-owned registration path.

    Provisional API: this function is excluded from the normal 1.x
    compatibility guarantee. Its signature or location may change, or it
    may be removed, in a future feature release.

    Forwards to the current Core ``backend.register_ordered_fold(source, fold)``.
    Registration-time validation, zero-SQL registration, exact-path
    ownership, and freeze behavior stay Core-owned until P2.
    """
    return backend.register_ordered_fold(source, fold)
