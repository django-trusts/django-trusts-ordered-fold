"""TrustsOrderedFoldModelBackend, family-local helpers, and E001."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core import checks as django_checks
from django.test import SimpleTestCase, TransactionTestCase
from django.test.utils import isolate_apps

from trusts.apps import TrustsImplementationConfig
from trusts.backends import TrustModelBackendMixin
from trusts.core import (
    BackendHandle,
    PlanQueryCompiler,
    TrustsRegistry,
)
from tests.helpers import (
    direct_models,
    handle,
    isolate_live_registry,
    live_fold_config,
    public_direct_fold,
    tables,
)
from trusts_ordered_fold import (
    OrderedFoldImplementationConfig,
    OrderedFoldRegistry,
    TrustsOrderedFoldModelBackend,
    granted,
    register_ordered_fold,
)
from trusts_ordered_fold.apps import OrderedFoldImplementationConfig as ConfigClass
from trusts_ordered_fold.checks import (
    CHECK_ID_ORDERED_FOLD_RENDERER,
    check_ordered_fold_renderer,
)
from trusts_ordered_fold.query import _ordered_fold_handles
from trusts_ordered_fold.registry import OrderedFoldQueryCompiler


FOLD_BACKEND = 'trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend'


class BackendSurfaceTest(SimpleTestCase):
    def test_concrete_backend_is_mixin_plus_model_backend(self):
        self.assertTrue(issubclass(TrustsOrderedFoldModelBackend, TrustModelBackendMixin))
        self.assertTrue(issubclass(TrustsOrderedFoldModelBackend, ModelBackend))
        self.assertIsInstance(
            TrustsOrderedFoldModelBackend.query_compiler,
            OrderedFoldQueryCompiler,
        )

    def test_config_overrides_protected_factories(self):
        self.assertEqual(
            OrderedFoldImplementationConfig._authorization_family,
            'ordered_fold',
        )
        self.assertFalse(
            hasattr(OrderedFoldImplementationConfig, 'authorization_family'),
        )
        self.assertIs(OrderedFoldImplementationConfig, ConfigClass)
        registry = OrderedFoldImplementationConfig._create_registry(
            None, FOLD_BACKEND,
        )
        self.assertIsInstance(registry, OrderedFoldRegistry)
        handle = OrderedFoldImplementationConfig._create_handle(
            None, FOLD_BACKEND, registry, OrderedFoldQueryCompiler(),
        )
        self.assertEqual(handle.path, FOLD_BACKEND)
        self.assertIs(handle.registry, registry)

    def test_e001_is_registered_on_package_import(self):
        registered = [
            check for check in django_checks.registry.registry.registered_checks
            if getattr(check, '__name__', '') == 'check_ordered_fold_renderer'
            and getattr(check, '__module__', '') == 'trusts_ordered_fold.checks'
        ]
        self.assertEqual(len(registered), 1)
        self.assertEqual(CHECK_ID_ORDERED_FOLD_RENDERER, 'trusts_ordered_fold.E001')


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class FamilyLocalAggregateTest(SimpleTestCase):
    def test_granted_omits_relationship_handles(self):
        Permission, Document, Ace = direct_models(suffix='Fam')
        fold = handle(path='tests.ordered-fold.family-fold')
        register_ordered_fold(
            fold, Ace, public_direct_fold(Ace, Permission, Document),
        )
        rel = BackendHandle(
            path='tests.ordered-fold.family-rel',
            registry=TrustsRegistry(),
            compiler=PlanQueryCompiler(),
        )
        self.assertEqual(_ordered_fold_handles((fold, rel)), (fold,))
        user = get_user_model()(username='probe')
        perm = Permission(codename='read_document')
        self.assertIsNone(granted((rel,), Document, user, perm))
        fold_q = granted((fold,), Document, user, perm)
        self.assertIsNotNone(fold_q)
        mixed_q = granted((fold, rel), Document, user, perm)
        self.assertIsNotNone(mixed_q)


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class VendorCheckOwnershipTest(TransactionTestCase):
    def test_e001_ignores_relationship_live_registry(self):
        Permission, Document, Ace = direct_models(suffix='RelChk')
        fold = OrderedFoldRegistry()
        register_ordered_fold(
            handle(fold), Ace, public_direct_fold(Ace, Permission, Document),
        )
        # A relationship-family owner must not be scanned even if a
        # leftover store somehow holds fold strategies.
        class RelConfig(TrustsImplementationConfig):
            name = 'tests'
            label = 'rel_chk'
            trusts_backend_paths = ('django.contrib.auth.backends.ModelBackend',)
            _authorization_family = 'relationship'

        from unittest.mock import patch

        live = live_fold_config()
        saved = dict(live.registries)
        try:
            with patch(
                'trusts.apps.implementation_configs',
                return_value=(),
            ):
                self.assertEqual(
                    check_ordered_fold_renderer(None, databases=['default']),
                    [],
                )
        finally:
            live.registries.clear()
            live.registries.update(saved)

    def test_e001_scans_only_fold_family_live_strategies(self):
        from django.db import connection

        Permission, Document, Ace = direct_models(suffix='FoldChk')
        registry = OrderedFoldRegistry()
        register_ordered_fold(
            handle(registry), Ace, public_direct_fold(Ace, Permission, Document),
        )
        live = live_fold_config()
        saved = dict(live.registries)
        isolate_live_registry(live, registry)
        try:
            messages = check_ordered_fold_renderer(None, databases=['default'])
            errors = [
                message for message in messages
                if message.id == CHECK_ID_ORDERED_FOLD_RENDERER
            ]
            if connection.vendor == 'postgresql':
                self.assertEqual(errors, [])
            else:
                self.assertEqual(len(errors), 1)
                self.assertIn('PostgreSQL', errors[0].msg)
        finally:
            live.registries.clear()
            live.registries.update(saved)


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class MixinInapplicabilityTest(TransactionTestCase):
    def test_inapplicable_object_is_zero_sql(self):
        Permission, Document, Ace = direct_models(suffix='Inapp')
        with tables(Permission, Document, Ace):
            backend = TrustsOrderedFoldModelBackend()
            user = get_user_model().objects.create_user(
                username='inapp', password='x',
            )
            with self.assertNumQueries(0):
                self.assertFalse(
                    backend.has_perm(user, 'trusts_ordered_fold_tests.read_document'),
                )
