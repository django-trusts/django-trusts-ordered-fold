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


def _auth_perm(model, codename):
    content_type = ContentType.objects.get_for_model(model)
    permission, _created = Permission.objects.get_or_create(
        content_type=content_type,
        codename=codename,
        defaults={'name': codename},
    )
    return permission


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

        class Document(models.Model):
            title = models.CharField(max_length=40)

            class Meta:
                app_label = 'tests'

        class Ace(models.Model):
            document = models.ForeignKey(Document, on_delete=models.CASCADE)
            permission = models.ForeignKey(
                Permission, null=True, on_delete=models.CASCADE,
            )
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            ace_order = models.IntegerField()
            ace_type = models.IntegerField()
            access_mask = models.BigIntegerField()

            class Meta:
                app_label = 'tests'

        self.Document = Document
        self.Ace = Ace
        self._tables = _tables(Document, Ace)
        self._tables.__enter__()
        self.alice = User.objects.create_user('alice-fold', password='x')
        self.bob = User.objects.create_user('bob-fold', password='x')
        self.read = _auth_perm(Document, 'read_document')
        self.write = _auth_perm(Document, 'write_document')
        self.readwrite = _auth_perm(Document, 'readwrite_document')
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

    def _agree(self, user, code, obj):
        """has_perm, .permitted(), and get_permitted_users name the same fact."""
        held = user.has_perm(code, obj)
        codename = code.split('.', 1)[1]
        permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(obj),
            codename=codename,
        )
        self.assertIs(self.has_perm(user, permission, obj), held)
        listed = set(
            PermittedQuerySet(model=type(obj)).permitted(
                code, user,
            ).values_list('pk', flat=True)
        )
        self.assertIs(obj.pk in listed, held)
        users = set(
            compile_permitted_users(obj, code).values_list('pk', flat=True)
        )
        self.assertIs(user.pk in users, held)

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
        self._agree(self.alice, 'tests.read_document', self.doc)
        self._agree(self.bob, 'tests.read_document', self.doc)
        self._agree(self.alice, 'tests.write_document', self.doc)
        self.assertEqual(
            self.backend.get_all_permissions(self.alice, self.doc), set(),
        )

    def test_inquiries_agree_on_null_and_other_trustee(self):
        clean = self.Document.objects.create(title='clean')
        denied = self.Document.objects.create(title='denied')
        null_order = self.Document.objects.create(title='null-order')
        foreign = self.Document.objects.create(title='foreign')
        self._ace(order=0, polarity=ALLOW, mask=0x1, document=clean)
        self._ace(order=0, polarity=DENY, mask=0x1, document=denied)
        self._ace(order=1, polarity=ALLOW, mask=0x1, document=denied)
        self._ace(order=1, polarity=ALLOW, mask=0x1, document=null_order)
        self._ace(order=0, polarity=ALLOW, mask=-1, user=self.bob, document=foreign)
        self._ace(order=1, polarity=ALLOW, mask=0x1, document=foreign)
        table = self.Ace._meta.db_table
        order_col = self.Ace._meta.get_field('ace_order').column
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL' % (
                    connection.ops.quote_name(table),
                    connection.ops.quote_name(order_col),
                ),
            )
            cursor.execute(
                'INSERT INTO %s (%s, %s, %s, %s, %s) VALUES (%%s, NULL, %%s, %%s, %%s)' % (
                    connection.ops.quote_name(table),
                    connection.ops.quote_name(self.Ace._meta.get_field('document').column),
                    connection.ops.quote_name(order_col),
                    connection.ops.quote_name(self.Ace._meta.get_field('ace_type').column),
                    connection.ops.quote_name(self.Ace._meta.get_field('access_mask').column),
                    connection.ops.quote_name(self.Ace._meta.get_field('user').column),
                ),
                [null_order.pk, ALLOW, 0x1, self.alice.pk],
            )
        for user in (self.alice, self.bob):
            for obj in (self.doc, self.other, clean, denied, null_order, foreign):
                self._agree(user, 'tests.read_document', obj)

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


@skipUnless(_postgres(), 'Ordered fold SQL is PostgreSQL-only.')
@override_settings(AUTHENTICATION_BACKENDS=(
    'tests.fold_host.backends.FoldHostBackend',
))
@isolate_apps(
    'tests', 'tests.fold_host',
    'django.contrib.auth', 'django.contrib.contenttypes',
)
class OrderedFoldColumnAgreementTests(TransactionTestCase):
    """PK versus to_field, and a renamed order column, agree on all three inquiries."""

    def test_to_field_and_db_column_agree(self):
        User = get_user_model()

        class Sheet(models.Model):
            code = models.CharField(max_length=20, unique=True)

            class Meta:
                app_label = 'tests'

        class Ace(models.Model):
            sheet = models.ForeignKey(
                Sheet, to_field='code', db_column='sheet_code',
                on_delete=models.CASCADE,
            )
            permission = models.ForeignKey(
                Permission, null=True, db_column='perm_id',
                on_delete=models.CASCADE,
            )
            user = models.ForeignKey(
                User, db_column='holder_id', on_delete=models.CASCADE,
            )
            ace_order = models.IntegerField(db_column='sort_key')
            ace_type = models.IntegerField(db_column='effect')
            access_mask = models.BigIntegerField(db_column='bits')

            class Meta:
                app_label = 'tests'

        with _tables(Sheet, Ace):
            alice = User.objects.create_user('alice-col', password='x')
            bob = User.objects.create_user('bob-col', password='x')
            _auth_perm(Sheet, 'read_sheet')
            allowed = Sheet.objects.create(code='allowed')
            denied = Sheet.objects.create(code='denied')
            empty = Sheet.objects.create(code='empty')
            Ace.objects.create(
                sheet=allowed, user=alice, ace_order=0, ace_type=ALLOW,
                access_mask=1,
            )
            Ace.objects.create(
                sheet=denied, user=alice, ace_order=0, ace_type=DENY,
                access_mask=1,
            )
            Ace.objects.create(
                sheet=denied, user=alice, ace_order=1, ace_type=ALLOW,
                access_mask=1,
            )
            backend = _install(lambda registry: registry.register(
                trust=Ace, user='user', permission='permission', content='sheet',
            ))
            catalog = backend._catalog()
            for user in (alice, bob):
                for obj in (allowed, denied, empty):
                    held = user.has_perm('tests.read_sheet', obj)
                    self.assertIs(
                        catalog.has_permission(
                            user, obj,
                            Permission.objects.get(
                                content_type=ContentType.objects.get_for_model(Sheet),
                                codename='read_sheet',
                            ),
                        ),
                        held,
                    )
                    listed = set(
                        PermittedQuerySet(model=Sheet).permitted(
                            'tests.read_sheet', user,
                        ).values_list('pk', flat=True)
                    )
                    self.assertIs(obj.pk in listed, held)
                    users = set(
                        compile_permitted_users(
                            obj, 'tests.read_sheet',
                        ).values_list('pk', flat=True)
                    )
                    self.assertIs(user.pk in users, held)
