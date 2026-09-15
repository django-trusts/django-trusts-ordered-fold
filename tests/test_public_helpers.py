"""Direct acceptance tests for family-local public helpers.

Covers ``authorization_required`` and ``common_permissions``: family
isolation, fail-closed guard preflight, and common-permission behavior.
Does not register ``trusts_ordered_fold.E002``; guard completeness is
runtime fail-closed.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission as AUTH_PERMISSION
from django.core import checks as django_checks
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import QuerySet
from django.http import Http404, HttpRequest
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from trusts.core import (
    BackendHandle,
    PlanQueryCompiler,
    TrustsConfigurationError,
    TrustsRegistry,
)
from tests.helpers import direct_models, handle, public_direct_fold
from trusts_ordered_fold import (
    authorization_required,
    common_permissions,
    register_ordered_fold,
)
from trusts_ordered_fold.registry import (
    FoldPlan,
    OrderedFoldBackendHandle,
    OrderedFoldQueryCompiler,
    OrderedFoldRegistry,
)


PERM = 'trusts_ordered_fold_tests.read_document'


def _request(user):
    request = HttpRequest()
    request.user = user
    request.META['SERVER_NAME'] = 'testserver'
    request.META['SERVER_PORT'] = '80'
    return request


def _user(**kwargs):
    fields = {'username': 'probe', 'pk': 1, 'is_active': True}
    fields.update(kwargs)
    return get_user_model()(**fields)


def _relationship_handle(path='tests.ordered-fold.family-rel'):
    return BackendHandle(
        path=path,
        registry=TrustsRegistry(),
        compiler=PlanQueryCompiler(),
    )


def _auth_permission_fold_handle(path='tests.ordered-fold.auth-guard'):
    class AuthPermissionRegistry(OrderedFoldRegistry):
        def plan_for(self, content, *, user=None, permission=None):
            return FoldPlan(
                records=(),
                permission_model=AUTH_PERMISSION,
                strategy=object(),
            )

    return OrderedFoldBackendHandle(
        path=path,
        registry=AuthPermissionRegistry(),
        compiler=OrderedFoldQueryCompiler(),
    )


def _guard(model, permission=PERM, conditions=()):
    @authorization_required(model, permission, conditions)
    def _view(request, pk=None):
        return 'ok'

    return _view


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class AuthorizationRequiredFamilyTest(SimpleTestCase):
    def test_relationship_handle_is_omitted_and_does_not_rescue_preflight(self):
        Permission, Document, Ace = direct_models(suffix='GuardRel')
        rel = _relationship_handle()
        view = _guard(Document)
        with patch(
            'trusts.apps.configured_implementation_handles',
            return_value=(rel,),
        ):
            with self.assertRaises(TrustsConfigurationError) as ctx:
                view(_request(_user()), pk=1)
        self.assertIn('no applicable auth.Permission', str(ctx.exception))

    def test_custom_permission_fold_fail_closes_without_using_relationship(self):
        Permission, Document, Ace = direct_models(suffix='GuardCustom')
        fold = handle(path='tests.ordered-fold.guard-custom')
        register_ordered_fold(
            fold, Ace, public_direct_fold(Ace, Permission, Document),
        )
        rel = _relationship_handle()
        view = _guard(Document)
        with patch(
            'trusts.apps.configured_implementation_handles',
            return_value=(rel, fold),
        ):
            with self.assertRaises(TrustsConfigurationError) as ctx:
                view(_request(_user()), pk=1)
        self.assertIn('no applicable auth.Permission', str(ctx.exception))

    def test_auth_permission_fold_preflight_sees_missing_condition(self):
        Permission, Document, Ace = direct_models(suffix='GuardAuth')
        fold = _auth_permission_fold_handle()
        rel = _relationship_handle()
        view = _guard(Document, conditions=('missing_guard',))
        with patch(
            'trusts.apps.configured_implementation_handles',
            return_value=(rel, fold),
        ):
            with self.assertRaises(TrustsConfigurationError) as ctx:
                view(_request(_user()), pk=1)
        message = str(ctx.exception)
        self.assertIn('missing_guard', message)
        self.assertIn('is not registered', message)
        self.assertNotIn('no applicable auth.Permission', message)

    def test_missing_pk_is_http404_before_preflight(self):
        Permission, Document, Ace = direct_models(suffix='GuardPk')
        view = _guard(Document)
        with self.assertRaises(Http404):
            view(_request(_user()))

    def test_inactive_and_anonymous_are_permission_denied(self):
        Permission, Document, Ace = direct_models(suffix='GuardPrin')
        view = _guard(Document)
        with self.assertRaises(PermissionDenied):
            view(_request(_user(is_active=False)), pk=1)
        with self.assertRaises(PermissionDenied):
            view(_request(AnonymousUser()), pk=1)


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class CommonPermissionsFamilyTest(SimpleTestCase):
    def test_relationship_handle_is_omitted(self):
        Permission, Document, Ace = direct_models(suffix='CommRel')
        fold = handle(path='tests.ordered-fold.comm-fold')
        register_ordered_fold(
            fold, Ace, public_direct_fold(Ace, Permission, Document),
        )
        rel = _relationship_handle()
        user = _user()
        candidate = Document(pk=1)
        fold_qs = common_permissions((fold,), candidate, user)
        rel_qs = common_permissions((rel,), candidate, user)
        mixed_qs = common_permissions((fold, rel), candidate, user)
        self.assertIsInstance(fold_qs, QuerySet)
        self.assertIs(fold_qs.model, Permission)
        self.assertIsNone(rel_qs)
        self.assertIsInstance(mixed_qs, QuerySet)
        self.assertIs(mixed_qs.model, Permission)

    def test_unmatched_content_returns_none(self):
        Permission, Document, Ace = direct_models(suffix='CommMiss')
        fold = handle(path='tests.ordered-fold.comm-miss')
        register_ordered_fold(
            fold, Ace, public_direct_fold(Ace, Permission, Document),
        )
        Other = type('OtherCommMiss', (models.Model,), {
            '__module__': __name__,
            'Meta': type('Meta', (), {'app_label': 'trusts_ordered_fold_tests'}),
        })
        self.assertIsNone(common_permissions((fold,), Other(pk=1), _user()))


class E002ScaffoldRemovedTest(SimpleTestCase):
    def test_fold_guard_does_not_register_e002(self):
        import trusts_ordered_fold.checks as checks_mod
        import trusts_ordered_fold.decorators as decorators_mod

        self.assertFalse(hasattr(decorators_mod, 'CHECK_ID_AUTHORIZATION_REQUIRED'))
        self.assertFalse(hasattr(decorators_mod, '_declared_authorization_guards'))
        self.assertFalse(hasattr(decorators_mod, '_remember_authorization_guard'))
        self.assertFalse(hasattr(checks_mod, 'CHECK_ID_AUTHORIZATION_REQUIRED'))
        registered = [
            check for check in django_checks.registry.registry.registered_checks
            if getattr(check, '__module__', '') == 'trusts_ordered_fold.checks'
        ]
        self.assertEqual(
            [check.__name__ for check in registered],
            ['check_ordered_fold_renderer'],
        )
