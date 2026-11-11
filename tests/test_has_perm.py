"""Single-object has_perm for the remaining-bits fold.

These are the original package's object-check scenarios: ordered ACE
rows, a permission codename mapped to bits, allow rows clearing
remaining bits, a deny row that touches a remaining bit, and the
original malformed-row gate. ``register()`` records the trust.
``.permitted()`` and ``get_permitted_users`` stay empty.
"""

from contextlib import contextmanager
from unittest import skipUnless

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.test import TransactionTestCase, override_settings
from django.test.utils import isolate_apps

from tests.fold_host.backends import FoldHostBackend
from trusts.backends import Recorder, compile_permitted_users
from trusts.compile.appbuild import build_app_catalog
from trusts.compile.compilers import RegistrationListener
from trusts.models import PermittedQuerySet
from trusts_ordered_fold.compiler import OrderedFoldQueryCompiler


ALLOW = 1
DENY = 2


def _postgres():
    return connection.vendor == 'postgresql'


@contextmanager
def _tables(*model_classes):
    with connection.schema_editor() as editor:
        for model in model_classes:
            editor.create_model(model)
    try:
        yield
    finally:
        with connection.schema_editor() as editor:
            for model in reversed(model_classes):
                editor.delete_model(model)


def _install(register, query_compiler=None):
    backend = FoldHostBackend()
    state = backend._state()
    if state is None:
        backend.get_registry()
        state = backend._state()
    state.recorder = Recorder(RegistrationListener())
    state.catalog = None
    state.query_compiler = query_compiler or type(backend).query_compiler
    register(state.recorder)
    config = apps.get_containing_app_config(type(backend).__module__)
    build_app_catalog(config, state)
    return backend


def _perm(permission_model, action, document_model):
    return permission_model.objects.create(
        codename='%s_%s' % (action, document_model._meta.model_name),
    )


@skipUnless(_postgres(), 'Ordered fold SQL is PostgreSQL-only.')
@override_settings(AUTHENTICATION_BACKENDS=(
    'tests.fold_host.backends.FoldHostBackend',
))
@isolate_apps(
    'tests', 'tests.fold_host',
    'django.contrib.auth', 'django.contrib.contenttypes',
)
class OrderedFoldHasPermTests(TransactionTestCase):
    """Port of OrderedFoldAuthorizationTest's single-object checks."""

    def setUp(self):
        User = get_user_model()

        class Perm(models.Model):
            codename = models.CharField(max_length=64)

            class Meta:
                app_label = 'tests'

        class Document(models.Model):
            title = models.CharField(max_length=40)

            class Meta:
                app_label = 'tests'

        class Ace(models.Model):
            document = models.ForeignKey(Document, on_delete=models.CASCADE)
            permission = models.ForeignKey(
                Perm, null=True, on_delete=models.CASCADE,
            )
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            ace_order = models.IntegerField()
            ace_type = models.IntegerField()
            access_mask = models.BigIntegerField()

            class Meta:
                app_label = 'tests'

        self.Perm = Perm
        self.Document = Document
        self.Ace = Ace
        self._tables = _tables(Perm, Document, Ace)
        self._tables.__enter__()
        self.alice = User.objects.create_user('alice-fold', password='x')
        self.bob = User.objects.create_user('bob-fold', password='x')
        self.read = _perm(Perm, 'read', Document)
        self.write = _perm(Perm, 'write', Document)
        self.readwrite = _perm(Perm, 'readwrite', Document)
        self.doc = Document.objects.create(title='target')
        self.other = Document.objects.create(title='other')
        self.backend = _install(lambda registry: registry.register(
            trust=Ace, user='user', permission='permission', content='document',
        ))

    def tearDown(self):
        state = self.backend._state()
        if state is not None:
            state.catalog = None
            state.recorder = Recorder(RegistrationListener())
        self._tables.__exit__(None, None, None)

    def has_perm(self, user, perm, obj):
        return self.backend._catalog().has_permission(user, obj, perm)

    def _ace(self, *, order, polarity, mask, user=None, document=None):
        return self.Ace.objects.create(
            document=document or self.doc,
            user=user or self.alice,
            ace_order=order,
            ace_type=polarity,
            access_mask=mask,
        )

    def test_allow_before_deny_allows_and_deny_before_allow_denies(self):
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        self._ace(order=1, polarity=DENY, mask=0x1)
        with self.assertNumQueries(1):
            self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)

        self.Ace.objects.all().delete()
        self._ace(order=0, polarity=DENY, mask=0x1)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        with self.assertNumQueries(1):
            self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

    def test_one_bit_and_multibit_identities(self):
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)
        self.assertIs(self.has_perm(self.alice, self.write, self.doc), False)
        self.assertIs(self.has_perm(self.alice, self.readwrite, self.doc), False)

        self._ace(order=1, polarity=ALLOW, mask=0x2)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)
        self.assertIs(self.has_perm(self.alice, self.write, self.doc), True)
        self.assertIs(self.has_perm(self.alice, self.readwrite, self.doc), True)

        self.Ace.objects.filter(access_mask=0x2).delete()
        self._ace(order=1, polarity=DENY, mask=0x2)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)
        self.assertIs(self.has_perm(self.alice, self.readwrite, self.doc), False)

    def test_missing_membership_grant_empty_bag_and_wrong_model(self):
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)
        self.assertIs(self.has_perm(self.bob, self.read, self.doc), False)
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.bob, self.read, self.doc), False)
        self.assertIs(self.has_perm(self.alice, self.read, self.other), False)

        class OtherPerm(models.Model):
            codename = models.CharField(max_length=64)

            class Meta:
                app_label = 'tests'

        with _tables(OtherPerm):
            other = OtherPerm.objects.create(codename='read_document')
            self.assertIs(
                self.backend._catalog().has_permission(
                    self.alice, self.doc, other,
                ),
                False,
            )

    def test_unknown_polarity_and_null_rows_gate_denial(self):
        self._ace(order=0, polarity=99, mask=0x1)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

        self.Ace.objects.all().delete()
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        table = self.Ace._meta.db_table
        order_field = self.Ace._meta.get_field('ace_order')
        columns = (
            self.Ace._meta.get_field('document').column,
            order_field.column,
            self.Ace._meta.get_field('ace_type').column,
            self.Ace._meta.get_field('access_mask').column,
            self.Ace._meta.get_field('user').column,
        )
        quoted = [connection.ops.quote_name(name) for name in columns]
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL' % (
                    connection.ops.quote_name(table),
                    connection.ops.quote_name(order_field.column),
                ),
            )
            cursor.execute(
                'INSERT INTO %s (%s) VALUES (%%s, NULL, %%s, %%s, %%s)' % (
                    connection.ops.quote_name(table),
                    ', '.join(quoted),
                ),
                [self.doc.pk, ALLOW, 0x1, self.alice.pk],
            )
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

    def test_negative_masks_gate_including_foreign_trustee(self):
        self._ace(order=0, polarity=ALLOW, mask=-1)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

        self.Ace.objects.all().delete()
        self._ace(order=0, polarity=DENY, mask=-1)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

        self.Ace.objects.all().delete()
        self._ace(order=0, polarity=ALLOW, mask=-1, user=self.bob)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

        self.Ace.objects.all().delete()
        self._ace(order=0, polarity=DENY, mask=-1, user=self.bob)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)

        self.Ace.objects.all().delete()
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)

        self.Ace.objects.all().delete()
        self._ace(order=0, polarity=ALLOW, mask=0)
        self._ace(order=1, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)

    def test_group_slice_does_not_grant(self):
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        plan = self.backend._catalog().plan_for(self.doc, user=self.alice)
        self.assertIsNone(plan.query_compiler.group_exists(
            plan, self.doc, self.alice, self.read,
        ))
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)

    def test_user_has_perm_string_uses_the_same_bits(self):
        content_type = ContentType.objects.get_for_model(self.Document)
        Permission.objects.get_or_create(
            content_type=content_type,
            codename='read_document',
            defaults={'name': 'read'},
        )
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        with self.assertNumQueries(1):
            self.assertIs(
                self.alice.has_perm('tests.read_document', self.doc), True,
            )
        self.assertIs(
            self.alice.has_perm('tests.write_document', self.doc), False,
        )

    def test_other_inquiries_do_not_overgrant(self):
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), True)
        self.assertEqual(
            self.backend.get_all_permissions(self.alice, self.doc), set(),
        )
        permitted = PermittedQuerySet(model=self.Document).permitted(
            'tests.read_document', self.alice,
        )
        self.assertEqual(list(permitted), [])
        self.assertEqual(
            list(compile_permitted_users(self.doc, self.read)), [],
        )

    def test_inactive_and_anonymous_deny(self):
        self._ace(order=0, polarity=ALLOW, mask=0x1)
        self.alice.is_active = False
        self.alice.save(update_fields=['is_active'])
        self.assertIs(self.has_perm(self.alice, self.read, self.doc), False)
        self.assertIs(AnonymousUser().has_perm('tests.read_document', self.doc), False)


@skipUnless(_postgres(), 'Ordered fold SQL is PostgreSQL-only.')
@override_settings(AUTHENTICATION_BACKENDS=(
    'tests.fold_host.backends.FoldHostBackend',
))
@isolate_apps(
    'tests', 'tests.fold_host',
    'django.contrib.auth', 'django.contrib.contenttypes',
)
class OrderedFoldFlatTokenHasPermTests(TransactionTestCase):
    """Port of the single-object flat-token check."""

    def test_direct_and_one_level_flat_group_token(self):
        User = get_user_model()

        class Perm(models.Model):
            codename = models.CharField(max_length=64)

            class Meta:
                app_label = 'tests'

        class Document(models.Model):
            title = models.CharField(max_length=40)

            class Meta:
                app_label = 'tests'

        class Identity(models.Model):
            code = models.CharField(max_length=16, unique=True)

            class Meta:
                app_label = 'tests'

        class Principal(models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            identity = models.ForeignKey(Identity, on_delete=models.CASCADE)

            class Meta:
                app_label = 'tests'

        class Membership(models.Model):
            member = models.ForeignKey(
                Identity, related_name='+', on_delete=models.CASCADE,
            )
            group = models.ForeignKey(
                Identity, related_name='+', on_delete=models.CASCADE,
            )

            class Meta:
                app_label = 'tests'

        class Ace(models.Model):
            document = models.ForeignKey(Document, on_delete=models.CASCADE)
            permission = models.ForeignKey(
                Perm, null=True, on_delete=models.CASCADE,
            )
            user = models.ForeignKey(
                User, null=True, on_delete=models.CASCADE,
            )
            trustee = models.ForeignKey(Identity, on_delete=models.CASCADE)
            ace_order = models.IntegerField()
            ace_type = models.IntegerField()
            access_mask = models.BigIntegerField()

            class Meta:
                app_label = 'tests'

        with _tables(Perm, Document, Identity, Principal, Membership, Ace):
            alice = User.objects.create_user('alice-token', password='x')
            stranger = User.objects.create_user('stranger-token', password='x')
            alice_sid = Identity.objects.create(code='alice')
            group_sid = Identity.objects.create(code='writers')
            Principal.objects.create(user=alice, identity=alice_sid)
            Membership.objects.create(member=alice_sid, group=group_sid)
            doc = Document.objects.create(title='shared')
            read = _perm(Perm, 'read', Document)
            Ace.objects.create(
                document=doc, ace_order=0, ace_type=ALLOW,
                access_mask=1, trustee=group_sid,
            )
            backend = _install(
                lambda registry: registry.register(
                    trust=Ace, user='user', permission='permission',
                    content='document',
                ),
                query_compiler=OrderedFoldQueryCompiler(
                    order='ace_order',
                    polarity='ace_type',
                    allow=ALLOW,
                    deny=DENY,
                    mask='access_mask',
                    trustee='trustee',
                    masks=(('read', 1),),
                    token=(Principal, Membership),
                ),
            )
            catalog = backend._catalog()
            self.assertIs(catalog.has_permission(alice, doc, read), True)
            self.assertIs(catalog.has_permission(stranger, doc, read), False)
            Membership.objects.all().delete()
            self.assertIs(catalog.has_permission(alice, doc, read), False)
