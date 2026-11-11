"""Remaining-bits fold for one object check.

``register()`` records the trust. For ``has_perm`` of one saved object
this compiler takes the content-correlated rows (every trustee, not
one permission identity) and runs the ordered remaining-bits scan.
Allow rows clear bits. A deny row that touches a remaining bit denies.
The object is granted when every requested bit has been cleared.
"""

from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.db.models import BooleanField, F, Model, Subquery

from trusts.errors import TrustsConfigurationError
from trusts.plan.relations import PlanQueryCompiler


class _RemainingBits(Subquery):
    """PostgreSQL remaining-bits EXISTS over one content-scoped witness."""

    output_field = BooleanField()

    def __init__(self, rows, *, permission, permission_model, content_model,
                 allow, deny, masks, user_pk, token_sql, token_params):
        super().__init__(rows, output_field=BooleanField())
        self.permission = permission
        self.permission_model = permission_model
        self.content_model = content_model
        self.allow = allow
        self.deny = deny
        self.masks = masks
        self.user_pk = user_pk
        self.token_sql = token_sql
        self.token_params = token_params

    def get_source_expressions(self):
        exprs = [self.query]
        permission = self.permission
        if (
            not isinstance(permission, Model)
            and hasattr(permission, 'resolve_expression')
        ):
            exprs.append(permission)
        return exprs

    def set_source_expressions(self, exprs):
        self.query = exprs[0]
        if len(exprs) > 1:
            self.permission = exprs[1]

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
            self.token_sql,
            mask_sql,
            ordinal, row_pk, polarity, mask,
            ordinal, row_pk,
            inner, quote('src'),
            trustee, polarity, ordinal, mask, mask, trustee,
            inner, quote('bad'),
            polarity, polarity, ordinal, mask, mask, trustee,
        )
        params = []
        params.extend(self.token_params)
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

    def combine(self, plan, witnesses):
        """This compiler does not OR. ``complete_exists`` answers instead."""
        return None

    def complete_exists(self, plan, candidates, user, permission):
        if connection.vendor != 'postgresql':
            return None
        if (
            not plan.records
            or plan.delegations
            or not isinstance(candidates, Model)
            or candidates.pk is None
            or not isinstance(user, Model)
            or user.pk is None
            or not self.masks
        ):
            return None
        for record in plan.records:
            if record.along is not None or record.via is not None:
                return None
        witnesses = plan.grant_witnesses('content_field')
        if len(witnesses) != 1:
            return None
        witness = witnesses[0]
        if witness.rows is None or witness.reach is not None:
            return None
        record = witness.record
        if (
            self._plain(record.root, self.order) is None
            or self._plain(record.root, self.polarity) is None
            or self._plain(record.root, self.mask) is None
            or self._column(record.root, self.trustee) is None
        ):
            return None
        permission_model = _asked_permission_model(permission, record)
        if permission_model is None:
            return None
        try:
            permission_model._meta.get_field('codename')
        except FieldDoesNotExist:
            return None
        token_sql, token_params = self._token(user)
        if token_sql is None:
            return None
        projected = witness.rows.values(
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
            user_pk=user.pk,
            token_sql=token_sql,
            token_params=token_params,
        )

    def _token(self, user):
        if self.token is None:
            return 'SELECT %s AS ident', (user.pk,)
        principal, membership = self.token
        try:
            user_col = self._column(principal, 'user')
            ident_col = self._column(principal, 'identity')
            member_col = self._column(membership, 'member')
            group_col = self._column(membership, 'group')
        except FieldDoesNotExist:
            return None, ()
        if None in (user_col, ident_col, member_col, group_col):
            return None, ()
        quote = connection.ops.quote_name
        sql = (
            'SELECT %s AS ident FROM %s WHERE %s = %%s '
            'UNION SELECT %s AS ident FROM %s WHERE %s IN ('
            'SELECT %s FROM %s WHERE %s = %%s)'
        ) % (
            quote(ident_col),
            quote(principal._meta.db_table),
            quote(user_col),
            quote(group_col),
            quote(membership._meta.db_table),
            quote(member_col),
            quote(ident_col),
            quote(principal._meta.db_table),
            quote(user_col),
        )
        return sql, (user.pk, user.pk)

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
