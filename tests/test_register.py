"""Registration acceptance, rejection, freeze, ownership, and zero-SQL."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TransactionTestCase
from django.test.utils import isolate_apps

from trusts.core import (
    BackendHandle,
    PlanQueryCompiler,
    Ref,
    TrustsConfigurationError,
    TrustsRegistry,
    _resolve_forward_singles,
    _resolve_path,
)
from trusts_ordered_fold.engine import validate_ordered_fold
from trusts_ordered_fold.registry import _public_path_segments

from tests.helpers import (
    ALLOW,
    DENY,
    direct_models,
    handle,
    public_direct_fold,
    tables,
)
from trusts_ordered_fold import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
    register_ordered_fold,
)


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class RegisterAcceptanceTest(SimpleTestCase):
    def test_public_fold_registers_on_the_given_backend(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        compiled = register_ordered_fold(
            backend, Ace, public_direct_fold(Ace, Permission, Document),
        )
        self.assertEqual(len(backend.registry.strategies), 1)
        self.assertEqual(backend.registry.records, ())
        self.assertIs(compiled.content_model, Document)
        self.assertIs(compiled.source_model, Ace)
        self.assertEqual(compiled.content_desc_path, ())
        self.assertEqual(len(compiled.source_desc_hops), 1)
        self.assertTrue(compiled.principal_is_user)
        self.assertIsNone(compiled.member_model)
        self.assertIs(
            backend.registry.strategies[0],
            compiled,
        )

    def test_function_matches_handle_method(self):
        Permission, Document, Ace = direct_models(suffix='Match')
        fold = public_direct_fold(Ace, Permission, Document)
        via_package = handle(path='tests.ordered-fold.via-package')
        via_handle = handle(path='tests.ordered-fold.via-handle')
        package_compiled = register_ordered_fold(via_package, Ace, fold)
        handle_compiled = via_handle.register_ordered_fold(Ace, fold)
        self.assertEqual(package_compiled, handle_compiled)

    def test_core_handle_is_rejected(self):
        Permission, Document, Ace = direct_models(suffix='Core')
        core_handle = BackendHandle(
            path='tests.ordered-fold.core-shim',
            registry=TrustsRegistry(),
            compiler=PlanQueryCompiler(),
        )
        with self.assertRaises(TrustsConfigurationError):
            register_ordered_fold(
                core_handle, Ace, public_direct_fold(Ace, Permission, Document),
            )
        self.assertFalse(hasattr(core_handle.registry, 'strategies'))
        self.assertFalse(hasattr(core_handle, 'register_ordered_fold'))


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class RegisterRejectionTest(SimpleTestCase):
    def test_ref_source_is_type_error(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        with self.assertRaises(TypeError):
            register_ordered_fold(
                backend,
                Ref(Ace),
                public_direct_fold(Ace, Permission, Document),
            )
        self.assertEqual(backend.registry.strategies, ())

    def test_ref_fold_fields_are_type_error(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        with self.assertRaises(TypeError):
            register_ordered_fold(backend, Ace, OrderedFold(
                content=Ref(Document),
                descriptor='',
                source_descriptor='document',
                order='ace_order',
                polarity=PolarityMap(
                    'ace_type', allow_value=ALLOW, deny_value=DENY,
                ),
                mask='access_mask',
                trustee='user',
                token=FlatToken(
                    principal=get_user_model(),
                    principal_user='',
                    principal_identity='',
                ),
                domain=PermissionMaskDomain(Permission, (MaskEntry('read', 1),)),
            ))
        self.assertEqual(backend.registry.strategies, ())

    def test_derived_source_argument_is_rejected(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        with self.assertRaises(TrustsConfigurationError):
            register_ordered_fold(backend, Ace, OrderedFold(
                content=Document,
                descriptor='',
                source=Ace,
                source_descriptor='document',
                order='ace_order',
                polarity=PolarityMap(
                    'ace_type', allow_value=ALLOW, deny_value=DENY,
                ),
                mask='access_mask',
                trustee='user',
                token=FlatToken(
                    principal=get_user_model(),
                    principal_user='',
                    principal_identity='',
                ),
                domain=PermissionMaskDomain(Permission, (MaskEntry('read', 1),)),
            ))
        self.assertEqual(backend.registry.strategies, ())

    def test_non_fold_is_rejected_without_mutation(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        with self.assertRaises(TrustsConfigurationError):
            register_ordered_fold(backend, Ace, object())
        self.assertEqual(backend.registry.strategies, ())

    def test_invalid_path_grammar_is_rejected_without_mutation(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        with self.assertRaises(TrustsConfigurationError):
            register_ordered_fold(backend, Ace, OrderedFold(
                content=Document,
                descriptor='',
                source_descriptor='',
                order='ace_order',
                polarity=PolarityMap(
                    'ace_type', allow_value=ALLOW, deny_value=DENY,
                ),
                mask='access_mask',
                trustee='user',
                token=FlatToken(
                    principal=get_user_model(),
                    principal_user='',
                    principal_identity='',
                ),
                domain=PermissionMaskDomain(Permission, (MaskEntry('read', 1),)),
            ))
        self.assertEqual(backend.registry.strategies, ())


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class RegisterFreezeTest(SimpleTestCase):
    def test_freeze_raises_before_path_resolution(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        backend.registry.freeze()
        with patch(
            'trusts_ordered_fold.registry._public_path_segments',
            wraps=_public_path_segments,
        ) as segments:
            with patch(
                'trusts.core._resolve_forward_singles',
                wraps=_resolve_forward_singles,
            ) as resolve:
                with patch(
                    'trusts.core._resolve_path',
                    wraps=_resolve_path,
                ) as anypath:
                    with patch(
                        'trusts_ordered_fold.engine.validate_ordered_fold',
                        wraps=validate_ordered_fold,
                    ) as validate:
                        with self.assertRaises(TrustsConfigurationError) as ctx:
                            register_ordered_fold(
                                backend,
                                Ace,
                                public_direct_fold(Ace, Permission, Document),
                            )
        self.assertIn('frozen', str(ctx.exception).lower())
        segments.assert_not_called()
        resolve.assert_not_called()
        anypath.assert_not_called()
        validate.assert_not_called()
        self.assertEqual(backend.registry.strategies, ())

    def test_freeze_wins_over_invalid_grammar(self):
        Permission, Document, Ace = direct_models()
        backend = handle()
        backend.registry.freeze()
        with self.assertRaises(TrustsConfigurationError) as ctx:
            register_ordered_fold(backend, Ace, OrderedFold(
                content=Document,
                descriptor='',
                source_descriptor='',
                order='ace_order',
                polarity=PolarityMap(
                    'ace_type', allow_value=ALLOW, deny_value=DENY,
                ),
                mask='access_mask',
                trustee='user',
                token=FlatToken(
                    principal=get_user_model(),
                    principal_user='',
                    principal_identity='',
                ),
                domain=PermissionMaskDomain(Permission, (MaskEntry('read', 1),)),
            ))
        self.assertIn('frozen', str(ctx.exception).lower())
        self.assertEqual(backend.registry.strategies, ())


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class RegisterOwnershipTest(SimpleTestCase):
    def test_dual_backend_registration_does_not_leak(self):
        Permission, Document, Ace = direct_models()
        fold = public_direct_fold(Ace, Permission, Document)
        left = handle(path='tests.ordered-fold.left')
        right = handle(path='tests.ordered-fold.right')
        register_ordered_fold(left, Ace, fold)
        self.assertEqual(len(left.registry.strategies), 1)
        self.assertEqual(right.registry.strategies, ())
        register_ordered_fold(right, Ace, fold)
        self.assertEqual(len(left.registry.strategies), 1)
        self.assertEqual(len(right.registry.strategies), 1)
        self.assertIsNot(
            left.registry.strategies[0],
            right.registry.strategies[0],
        )
        self.assertEqual(
            left.registry.strategies[0],
            right.registry.strategies[0],
        )
        self.assertEqual(left.path, 'tests.ordered-fold.left')
        self.assertEqual(right.path, 'tests.ordered-fold.right')
        self.assertIsNot(left.registry, right.registry)


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class RegisterZeroSqlTest(TransactionTestCase):
    def test_accepted_and_rejected_registration_are_zero_sql(self):
        Permission, Document, Ace = direct_models()
        fold = public_direct_fold(Ace, Permission, Document)
        with tables(Permission, Document, Ace):
            backend = handle(path='tests.ordered-fold.zero-sql')
            with self.assertNumQueries(0):
                compiled = register_ordered_fold(backend, Ace, fold)
            with self.assertNumQueries(0):
                with self.assertRaises(TrustsConfigurationError):
                    register_ordered_fold(backend, Ace, object())
            frozen = handle(path='tests.ordered-fold.zero-sql-frozen')
            frozen.registry.freeze()
            with self.assertNumQueries(0):
                with self.assertRaises(TrustsConfigurationError):
                    register_ordered_fold(frozen, Ace, fold)
        self.assertIs(compiled.content_model, Document)
        self.assertEqual(len(backend.registry.strategies), 1)
        self.assertEqual(frozen.registry.strategies, ())
