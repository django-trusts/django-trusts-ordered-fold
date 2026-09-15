"""Family-local OrderedFold QuerySet, grant, and common-permission helpers."""

from django.db.models import Manager, Model, QuerySet

from trusts.core import TrustsConfigurationError, _compile_common_permissions, _compile_granted
from trusts.query import is_active_principal  # re-exported for callers


def _is_ordered_fold_handle(handle, apps_registry=None):
    from trusts.apps import _handle_authorization_family
    from trusts_ordered_fold.registry import (
        OrderedFoldBackendHandle,
        OrderedFoldRegistry,
    )

    if isinstance(handle, OrderedFoldBackendHandle):
        return True
    if isinstance(getattr(handle, 'registry', None), OrderedFoldRegistry):
        return True
    return _handle_authorization_family(handle, apps_registry) == 'ordered_fold'


def _ordered_fold_handles(handles, apps_registry=None):
    return tuple(
        handle for handle in handles
        if _is_ordered_fold_handle(handle, apps_registry)
    )


def _ordered_fold_implementation_handles(apps_registry=None):
    from trusts.apps import configured_implementation_handles

    return _ordered_fold_handles(
        configured_implementation_handles(apps_registry),
        apps_registry,
    )


def granted(handles, candidates, user, permission, *, kind='complete'):
    """OR each applicable OrderedFold-family handle's complete predicate.

    Extension-owned aggregate: relationship-family handles are omitted.
    Mixin instance / QuerySet evaluation still uses Core
    ``_compile_granted`` on ``self._own_handle()``.
    """
    return _compile_granted(
        _ordered_fold_handles(handles),
        candidates, user, permission, kind=kind,
    )


def common_permissions(handles, candidates, user, *, kind='complete'):
    """Permission queryset held on every candidate via the fold proof.

    Extension-owned aggregate: relationship-family handles are omitted.
    """
    return _compile_common_permissions(
        _ordered_fold_handles(handles),
        candidates, user, kind=kind,
    )


class AuthorizedQuerySet(QuerySet):
    """Instance-only authorized-row filter over OrderedFold handles.

    ``permission`` must be a model instance. Core relationship
    ``.authorized`` is a different family and is not mixed here.
    """

    def authorized(self, user, permission, extra_q=None):
        if not isinstance(permission, Model):
            raise TrustsConfigurationError(
                'permission must be a model instance, not %r.' % (permission,)
            )
        granted_q = granted(
            _ordered_fold_implementation_handles(),
            self, user, permission, kind='complete',
        )
        if granted_q is None:
            return self.none()
        if extra_q is not None:
            granted_q = granted_q & extra_q
        return self.filter(granted_q).distinct()


AuthorizedManager = Manager.from_queryset(AuthorizedQuerySet)

__all__ = (
    'AuthorizedManager',
    'AuthorizedQuerySet',
    'common_permissions',
    'granted',
    'is_active_principal',
)
