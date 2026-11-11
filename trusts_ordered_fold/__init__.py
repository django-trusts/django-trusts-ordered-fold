"""PostgreSQL ordered allow/deny for one django-trusts object check.

The application registers trust rows with ``register()``. This package
replaces only how the applicable rows combine: the first row by
``(order, pk)`` wins, and an unknown polarity denies.

This round answers ``has_perm(user, perm, obj)`` for one saved object.
``.permitted()`` and ``get_permitted_users`` are not folded.
"""

from trusts_ordered_fold.backends import TrustsOrderedFoldModelBackend
from trusts_ordered_fold.compiler import OrderedFoldQueryCompiler

__all__ = (
    'OrderedFoldQueryCompiler',
    'TrustsOrderedFoldModelBackend',
)
