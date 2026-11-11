"""PostgreSQL remaining-bits authorization for django-trusts.

The application registers trust rows with ``register()``. This package
replaces how those rows combine. ACE rows on one object are walked in
``(order, pk)`` order. The requested permission maps to bits. An allow
row clears its bits. A deny row that touches a remaining bit denies.
The check grants when every requested bit is cleared. A NULL order,
polarity, mask, or trustee, a negative mask, or any other polarity
denies, including a row for another trustee.

``has_perm`` and ``.permitted()`` run that same statement.
"""

from trusts_ordered_fold.backends import TrustsOrderedFoldModelBackend
from trusts_ordered_fold.compiler import OrderedFoldQueryCompiler

__all__ = (
    'OrderedFoldQueryCompiler',
    'TrustsOrderedFoldModelBackend',
)
