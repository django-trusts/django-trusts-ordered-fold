"""Remaining-bits fold for one object check.

``register()`` records the trust. For ``has_perm`` of one saved object
this compiler takes the content-correlated rows (every trustee, not
one permission identity) and runs the ordered remaining-bits scan.
Allow rows clear bits. A deny row that touches a remaining bit denies.
The object is granted when every requested bit has been cleared.
"""

from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.db.models import (
    BooleanField, F, Model, OuterRef, Q, QuerySet, Subquery,
)

from trusts.errors import TrustsConfigurationError
from trusts.plan.predicates import bind_record_qs
from trusts.plan.relations import PlanQueryCompiler


class _RemainingBits(Subquery):
    """PostgreSQL remaining-bits EXISTS over one content-scoped witness."""

    output_field = BooleanField()

    def __init__(self, rows, *, permission, permission_model, content_model,
                 allow, deny, masks, token, user_pk=None, user_ref=None):
        super().__init__(rows, output_field=BooleanField())
        self.permission = permission
        self.permission_model = permission_model
        self.content_model = content_model
        self.allow = allow
        self.deny = deny
        self.masks = masks
        self.token = token
        self.user_pk = user_pk
        self.user_ref = user_ref

    def get_source_expressions(self):
        exprs = [self.query]
        if self.user_ref is not None:
            exprs.append(self.user_ref)
        permission = self.permission
        if (
            not isinstance(permission, Model)
            and hasattr(permission, 'resolve_expression')
        ):
            exprs.append(permission)
        return exprs

    def set_source_expressions(self, exprs):
        self.query = exprs[0]
        index = 1
        if self.user_ref is not None:
            self.user_ref = exprs[index]
            index += 1
        if index < len(exprs):
            self.permission = exprs[index]

    def as_sql(self, compiler, connection, template=None, **extra_context):
        if connection.vendor != 'postgresql':
            raise TrustsConfigurationError(
                'Ordered fold SQL is PostgreSQL-only.'
            )
        witness_sql, witness_params = self.query.as_sql(compiler, connection)
        inner = witness_sql[1:-1]
        quote = connection.ops.quote_name
        ordinal = quote('fold_ord')
        polarity = quote('fold_polarity')
        mask = quote('fold_mask')
        trustee = quote('fold_trustee')
        row_pk = quote('fold_pk')
        if self.user_ref is not None:
            user_sql, user_params = compiler.compile(self.user_ref)
        else:
            user_sql, user_params = '%s', (self.user_pk,)
        user_params = tuple(user_params)
        token_sql, token_params = _token_sql(self.token, user_sql, connection)
        if token_sql is None:
            return 'FALSE', ()
        perm_sql, perm_params = _permission_pk_sql(self.permission, compiler)
        mask_sql, mask_params = _mask_sql(
            connection, self.permission_model, self.content_model,
            self.masks, perm_sql,
        )
        sql = (
            'EXISTS ('
            'WITH RECURSIVE '
            'of_token AS (%s), '
            'requested AS (%s), '
            'numbered AS ('
            'SELECT %s, %s, %s AS polarity, %s::bigint AS mask, '
            'ROW_NUMBER() OVER (ORDER BY %s, %s) AS rn '
            'FROM (%s) %s '
            'WHERE %s IN (SELECT ident FROM of_token) '
            'AND %s IN (%%s, %%s) '
            'AND %s IS NOT NULL AND %s IS NOT NULL '
            'AND %s >= 0 AND %s IS NOT NULL'
            '), '
            'scan AS ('
            'SELECT 0::bigint AS step, '
            '(SELECT mask FROM requested)::bigint AS remaining, '
            'FALSE AS denied '
            'UNION ALL '
            'SELECT n.rn, '
            'CASE WHEN s.remaining IS NULL THEN NULL '
            'WHEN n.polarity IS NOT DISTINCT FROM %%s '
            'THEN s.remaining & ~n.mask ELSE s.remaining END, '
            'COALESCE(s.denied, FALSE) OR ('
            'n.polarity IS NOT DISTINCT FROM %%s AND s.remaining IS NOT NULL '
            'AND (s.remaining & n.mask) <> 0'
            ') '
            'FROM scan s INNER JOIN numbered n ON n.rn = s.step + 1 '
            'WHERE NOT COALESCE(s.denied, FALSE) '
            'AND s.remaining IS DISTINCT FROM 0'
            ') '
            'SELECT 1 FROM requested WHERE NOT EXISTS ('
            'SELECT 1 FROM (%s) %s WHERE ('
            '%s IS DISTINCT FROM %%s AND %s IS DISTINCT FROM %%s'
            ') OR %s IS NULL OR %s IS NULL OR %s < 0 OR %s IS NULL'
            ') AND ('
            'SELECT remaining = 0 AND NOT denied FROM scan '
            'ORDER BY step DESC LIMIT 1'
            '))'
        ) % (
            token_sql,
            mask_sql,
            ordinal, row_pk, polarity, mask,
            ordinal, row_pk,
            inner, quote('src'),
            trustee, polarity, ordinal, mask, mask, trustee,
            inner, quote('bad'),
            polarity, polarity, ordinal, mask, mask, trustee,
        )
        params = []
        params.extend(user_params)
        params.extend(token_params)
        params.extend(user_params if self.token else ())
        params.extend(mask_params)
        params.extend(perm_params)
        params.extend(witness_params)
        params.extend((self.allow, self.deny))
        params.extend((self.allow, self.deny))
        params.extend(witness_params)
        params.extend((self.allow, self.deny))
        return sql, tuple(params)


def _asked_permission_model(permission, record):
    """Model whose ``codename`` selects the mask.

    An instance has to be the registration's permission model. A
    codename subquery (``has_perm``'s string form) carries its own model.
    """
    if isinstance(permission, Model):
        if permission.pk is None:
            return None
        model = permission._meta.concrete_model
        if model is not record.permission_model._meta.concrete_model:
            return None
        return model
    model = getattr(getattr(permission, 'query', None), 'model', None)
    if model is None:
        return record.permission_model
    return model._meta.concrete_model


def _permission_pk_sql(permission, compiler):
    if isinstance(permission, Model):
        return '%s', (permission.pk,)
    compiled, params = compiler.compile(permission)
    return compiled, tuple(params)


def _mask_sql(connection, permission_model, content_model, masks, perm_sql):
    quote = connection.ops.quote_name
    codename = permission_model._meta.get_field('codename')
    values = ', '.join('(%s, %s)' for _ in masks)
    params = []
    model_name = content_model._meta.model_name
    for action, mask in masks:
        params.append('%s_%s' % (action, model_name))
        params.append(mask)
    sql = (
        'SELECT maskmap.mask FROM (VALUES %s) AS maskmap(codename, mask) '
        'INNER JOIN %s %s ON %s.%s = maskmap.codename '
        'WHERE %s.%s = %s'
    ) % (
        values,
        quote(permission_model._meta.db_table),
        quote('perm'),
        quote('perm'),
        quote(codename.column),
        quote('perm'),
        quote(permission_model._meta.pk.column),
        perm_sql,
    )
    return sql, tuple(params)


def _token_sql(token, user_sql, connection):
    """Identity set. ``user_sql`` is the candidate user's primary key."""
    if token is None:
        return 'SELECT (%s) AS ident' % user_sql, ()
    principal, membership = token
    quote = connection.ops.quote_name

    def column(model, name):
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            return None
        return getattr(field, 'column', None) or None

    user_col = column(principal, 'user')
    ident_col = column(principal, 'identity')
    member_col = column(membership, 'member')
    group_col = column(membership, 'group')
    if None in (user_col, ident_col, member_col, group_col):
        return None, ()
    sql = (
        'SELECT %s AS ident FROM %s WHERE %s = (%s) '
        'UNION SELECT %s AS ident FROM %s WHERE %s IN ('
        'SELECT %s FROM %s WHERE %s = (%s))'
    ) % (
        quote(ident_col),
        quote(principal._meta.db_table),
        quote(user_col),
        user_sql,
        quote(group_col),
        quote(membership._meta.db_table),
        quote(member_col),
        quote(ident_col),
        quote(principal._meta.db_table),
        quote(user_col),
        user_sql,
    )
    return sql, ()


class OrderedFoldQueryCompiler(PlanQueryCompiler):
    """Object-check compiler. Other inquiries do not OR these rows.

    ``masks`` is ``(action, bits)``. The requested permission's
    codename is ``action`` plus the content model's name. ``token``
    is an optional ``(principal, membership)`` pair. Without it the
    trustee column is the asking user's primary key.
    """

    def __init__(self, *, order, polarity, allow, deny, mask, trustee,
                 masks, token=None):
        self.order = order
        self.polarity = polarity
        self.allow = allow
        self.deny = deny
        self.mask = mask
        self.trustee = trustee
        self.masks = tuple(masks)
        self.token = token

    def replaces_grant(self):
        return True

    def combine(self, plan, witnesses):
        """This compiler does not OR. The fold predicate answers instead."""
        return None

    def complete_exists(self, plan, candidates, user, permission):
        """Content-side fold. One object or a content queryset."""
        if not isinstance(user, Model) or user.pk is None:
            return None
        if isinstance(candidates, Model):
            if candidates.pk is None:
                return None
        elif not isinstance(candidates, QuerySet):
            return None
        rows = self._content_rows(plan)
        if rows is None:
            return None
        return self._fold(plan, rows, permission, user_pk=user.pk)

    def users_exist(self, plan, content, permission):
        """Same fold, with the candidate user as the outer row."""
        if not isinstance(content, Model) or content.pk is None:
            return None
        record = self._record(plan)
        if record is None:
            return None
        try:
            bound = getattr(content, record.content_target)
        except AttributeError:
            return None
        rows = bind_record_qs(
            record,
            correlation=Q(**{record.content_field: bound}),
            content_identity=plan.content_identity or content.__class__,
        )
        return self._fold(
            plan, rows, permission,
            user_ref=OuterRef(record.user_model._meta.pk.attname),
        )

    def _record(self, plan):
        if (
            connection.vendor != 'postgresql'
            or not plan.records
            or plan.delegations
            or not self.masks
            or len(plan.records) != 1
        ):
            return None
        record = plan.records[0]
        if record.along is not None or record.via is not None:
            return None
        if (
            self._plain(record.root, self.order) is None
            or self._plain(record.root, self.polarity) is None
            or self._plain(record.root, self.mask) is None
            or self._column(record.root, self.trustee) is None
        ):
            return None
        return record

    def _content_rows(self, plan):
        record = self._record(plan)
        if record is None:
            return None
        witnesses = plan.grant_witnesses('content_field')
        if len(witnesses) != 1:
            return None
        witness = witnesses[0]
        if witness.rows is None or witness.reach is not None:
            return None
        return witness.rows

    def _fold(self, plan, rows, permission, *, user_pk=None, user_ref=None):
        record = plan.records[0]
        permission_model = _asked_permission_model(permission, record)
        if permission_model is None:
            return None
        try:
            permission_model._meta.get_field('codename')
        except FieldDoesNotExist:
            return None
        if self.token is not None and _token_sql(self.token, '%s', connection)[0] is None:
            return None
        projected = rows.values(
            fold_ord=F(self.order),
            fold_pk=F('pk'),
            fold_polarity=F(self.polarity),
            fold_mask=F(self.mask),
            fold_trustee=F(self.trustee),
        )
        return _RemainingBits(
            projected,
            permission=permission,
            permission_model=permission_model,
            content_model=record.content_model,
            allow=self.allow,
            deny=self.deny,
            masks=self.masks,
            token=self.token,
            user_pk=user_pk,
            user_ref=user_ref,
        )

    @staticmethod
    def _plain(model, name):
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            return None
        if not getattr(field, 'concrete', False) or field.is_relation:
            return None
        return field

    @staticmethod
    def _column(model, name):
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            return None
        column = getattr(field, 'column', None)
        if not column:
            return None
        return column
