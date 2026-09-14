"""Fixed-query and named-filter restrict proofs (ported from Core #187)."""

from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import isolate_apps

from trusts.core import TrustsConfigurationError, all_match
from tests.helpers import handle, tables
from tests.test_issue100 import (
    ALLOW,
    DENY,
    _direct_models,
    _handles,
    _perm,
    _postgres,
    _register_direct,
)
from trusts_ordered_fold import register_ordered_fold
from trusts_ordered_fold.engine import OrderedFoldAllowed


@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class VendorFailClosedTest(TransactionTestCase):
    def test_applicable_fold_raises_on_non_postgres_without_cte(self):
        Permission, Document, Ace = _direct_models(suffix='Fail')
        with tables(Permission, Document, Ace):
            User = get_user_model()
            alice = User.objects.create_user(username='alice-fail', password='x')
            doc = Document.objects.create(title='d')
            read = _perm(Permission, 'read', Document)
            Ace.objects.create(
                document=doc, ace_order=0, ace_type=ALLOW,
                access_mask=1, user=alice,
            )
            registry = handle().registry
            compiled = _register_direct(registry, Ace, Permission, Document)
            expr = OrderedFoldAllowed(compiled, alice, read)
            compiler = Document.objects.filter(pk=doc.pk).query.get_compiler('default')

            class Stub(object):
                vendor = 'mysql'
                alias = 'other'
                settings_dict = {'ENGINE': 'django.db.backends.mysql'}
                ops = connection.ops

            with self.assertRaises(TrustsConfigurationError) as ctx:
                expr.as_sql(compiler, Stub())
            message = str(ctx.exception).lower()
            self.assertIn('postgresql', message)
            self.assertIn('mysql', message)
            self.assertNotIn('with recursive', message)


@skipUnless(_postgres(), 'OrderedFold renderer is PostgreSQL')
@isolate_apps(
    'tests',
    'django.contrib.auth',
    'django.contrib.contenttypes',
)
class FixedQueryTest(TransactionTestCase):
    def test_each_evaluated_projection_is_one_sql(self):
        Permission, Document, Ace = _direct_models(suffix='Fixed')
        with tables(Permission, Document, Ace):
            User = get_user_model()
            alice = User.objects.create_user(username='alice-fixed', password='x')
            doc = Document.objects.create(title='kept')
            other = Document.objects.create(title='other')
            read = _perm(Permission, 'read', Document)
            Ace.objects.create(
                document=doc, ace_order=0, ace_type=ALLOW,
                access_mask=1, user=alice,
            )
            registry = handle().registry
            _register_direct(registry, Ace, Permission, Document)
            handles = _handles(registry)
            with self.assertNumQueries(1):
                self.assertTrue(registry.has_permission(alice, doc, read))
            with self.assertNumQueries(1):
                self.assertFalse(registry.has_permission(alice, other, read))
            with self.assertNumQueries(1):
                self.assertTrue(all_match(handles, doc, alice, read))
            qs = Document.objects.filter(pk__in=[doc.pk, other.pk])
            with self.assertNumQueries(1):
                self.assertFalse(all_match(handles, qs, alice, read))

    def test_named_filter_restricts_and_never_creates(self):
        Permission, Document, Ace = _direct_models(suffix='Filt')
        with tables(Permission, Document, Ace):
            User = get_user_model()
            alice = User.objects.create_user(username='alice-filt', password='x')
            kept = Document.objects.create(title='kept')
            nope = Document.objects.create(title='nope')
            read = _perm(Permission, 'read', Document)
            Ace.objects.create(
                document=kept, ace_order=0, ace_type=ALLOW,
                access_mask=1, user=alice,
            )
            Ace.objects.create(
                document=nope, ace_order=0, ace_type=ALLOW,
                access_mask=1, user=alice,
            )
            backend = handle()
            _register_direct(backend.registry, Ace, Permission, Document)
            backend.add_named_filter(
                Document, 'titled',
                lambda u, p, o: o.title == 'kept',
            )
            extra = backend.registry.condition_lookup.compile_q(
                Document, 'read_document:titled', alice,
            )
            self.assertTrue(
                backend.registry.has_permission(alice, kept, read),
            )
            self.assertTrue(
                backend.registry.has_permission(alice, nope, read),
            )
            handles = _handles(backend.registry)
            with self.assertNumQueries(1):
                self.assertTrue(
                    all_match(handles, kept, alice, read, extra_q=extra),
                )
            with self.assertNumQueries(1):
                self.assertFalse(
                    all_match(handles, nope, alice, read, extra_q=extra),
                )
            empty = handle(path='tests.ordered-fold.filter-only')
            empty.add_named_filter(
                Document, 'titled',
                lambda u, p, o: o.title == 'kept',
            )
            extra_only = empty.registry.condition_lookup.compile_q(
                Document, 'read_document:titled', alice,
            )
            self.assertIsNone(
                all_match(_handles(empty.registry), kept, alice, read, extra_q=extra_only),
            )
