"""Concrete ordered-fold Django backend.

Subclass this, set ``query_compiler`` to an
``OrderedFoldQueryCompiler``, and list that subclass in
``AUTHENTICATION_BACKENDS``. The subclass's app config extends
``TrustsConfigMixin``. The application still calls ``register()``.
"""

from django.contrib.auth.backends import ModelBackend

from trusts.backends import TrustModelBackendMixin
from trusts_ordered_fold.compiler import OrderedFoldQueryCompiler


class _DenyFold(OrderedFoldQueryCompiler):
    """Unconfigured fold. Denies, and does not fall through to OR."""

    def __init__(self):
        super().__init__(
            order='ace_order', polarity='ace_type', allow=1, deny=2,
            mask='access_mask', trustee='user', masks=(),
        )

    def complete_exists(self, plan, candidates, user, permission):
        return None


class TrustsOrderedFoldModelBackend(TrustModelBackendMixin, ModelBackend):
    """Object-permission backend. ``has_perm`` folds; other inquiries deny.

    ``family`` is not ``relationship``, so ``.permitted()`` does not OR
    this catalog. ``query_compiler`` on a subclass names the order and
    polarity fields.
    """

    family = 'ordered_fold'
    query_compiler = _DenyFold()

    def get_all_permissions(self, user_obj, obj=None, **skip_flags):
        """Permission enumeration is not this fold. Empty, not an OR."""
        return set()

    def get_group_permissions(self, user_obj, obj=None, **skip_flags):
        return set()
