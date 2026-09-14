"""Extension-owned OrderedFold registry, handle, compiler, and registration.

Topology A: this store holds OrderedFold plans and named filters only.
It does not register relationships or compose a mixed family plan.
"""

from dataclasses import dataclass

from django.db.models import Model, Q, QuerySet
from django.db.models.base import ModelBase

from trusts.core import (
    QueryCompiler,
    Ref,
    TrustsConfigurationError,
    _bind_terminal,
    _concrete_model,
    _content_model,
    _require_instance,
    candidate_queryset,
)
from trusts_ordered_fold.engine import (
    FlatToken,
    OrderedFold,
    OrderedFoldAllowed,
    PolarityMap,
    validate_ordered_fold,
)


def _is_model_class(value):
    return isinstance(value, ModelBase)


def _public_path_segments(value, role, *, allow_empty=False):
    """Split a public Django ``__`` path. Reject before ``Ref`` / resolve."""
    if isinstance(value, Ref):
        raise TypeError(
            '%s must be a Django path string, not a Ref.' % (role,)
        )
    if not isinstance(value, str):
        raise TrustsConfigurationError(
            '%s must be a Django path string, not %r.' % (role, value)
        )
    if not value:
        if allow_empty:
            return ()
        raise TrustsConfigurationError(
            '%s path %r is not a valid Django __ relationship path.'
            % (role, value)
        )
    if (
        value.startswith('__')
        or value.endswith('__')
        or '.' in value
    ):
        raise TrustsConfigurationError(
            '%s path %r is not a valid Django __ relationship path.'
            % (role, value)
        )
    segments = value.split('__')
    if any(segment == '' for segment in segments):
        raise TrustsConfigurationError(
            '%s path %r is not a valid Django __ relationship path.'
            % (role, value)
        )
    return tuple(segments)


def _public_ref(root, value, role, *, allow_empty=False):
    return Ref(root, _public_path_segments(
        value, role, allow_empty=allow_empty,
    ))


def _public_model_class(value, role):
    if isinstance(value, Ref):
        raise TypeError(
            '%s must be a Django model class, not a Ref.' % (role,)
        )
    if isinstance(value, str):
        raise TypeError(
            '%s must be a Django model class, not a path string.' % (role,)
        )
    if not _is_model_class(value):
        raise TrustsConfigurationError(
            '%s must be a Django model class, not %r.' % (role, value)
        )
    return value


def _reject_public_ref(value, role):
    if isinstance(value, Ref):
        raise TypeError(
            '%s must be a Django path string, not a Ref.' % (role,)
        )
    return value


def _bind_public_flat_token(token):
    """Bind public FlatToken model/path fields to independent Ref roots."""
    if not isinstance(token, FlatToken):
        return token
    principal = _public_model_class(token.principal, 'principal')
    principal_user = _public_ref(
        principal, token.principal_user, 'principal_user', allow_empty=True,
    )
    principal_identity = _public_ref(
        principal, token.principal_identity, 'principal_identity',
        allow_empty=True,
    )
    member = token.member
    member_identity = token.member_identity
    member_group = token.member_group
    if member is None and member_identity is None and member_group is None:
        return FlatToken(
            principal=Ref(principal),
            principal_user=principal_user,
            principal_identity=principal_identity,
        )
    if member is None:
        _reject_public_ref(member_identity, 'member_identity')
        _reject_public_ref(member_group, 'member_group')
        return FlatToken(
            principal=Ref(principal),
            principal_user=principal_user,
            principal_identity=principal_identity,
            member=None,
            member_identity=member_identity,
            member_group=member_group,
        )
    member = _public_model_class(member, 'member')
    if member_identity is not None:
        member_identity = _public_ref(
            member, member_identity, 'member_identity',
        )
    else:
        _reject_public_ref(member_identity, 'member_identity')
    if member_group is not None:
        member_group = _public_ref(member, member_group, 'member_group')
    else:
        _reject_public_ref(member_group, 'member_group')
    return FlatToken(
        principal=Ref(principal),
        principal_user=principal_user,
        principal_identity=principal_identity,
        member=Ref(member),
        member_identity=member_identity,
        member_group=member_group,
    )


def _bind_public_polarity(source_model, polarity):
    if not isinstance(polarity, PolarityMap):
        return polarity
    if isinstance(polarity.field, Ref):
        raise TypeError(
            'PolarityMap.field must be a Django path string, not a Ref.'
        )
    return PolarityMap(
        _public_ref(source_model, polarity.field, 'polarity'),
        allow_value=polarity.allow_value,
        deny_value=polarity.deny_value,
    )


def bind_public_ordered_fold(source_model, strategy):
    """Normalize public OrderedFold models/paths to internal Refs."""
    if not isinstance(strategy, OrderedFold):
        raise TrustsConfigurationError(
            'register_ordered_fold requires OrderedFold, not %r.'
            % (strategy,)
        )
    if isinstance(strategy.source, Ref) or isinstance(
        strategy.source_descriptor, Ref,
    ):
        raise TypeError(
            'register_ordered_fold does not accept Ref fields; pass '
            'Django path strings.'
        )
    if strategy.source is not None:
        raise TrustsConfigurationError(
            'source is derived from the source model passed to '
            'register_ordered_fold.'
        )
    content_model = _public_model_class(strategy.content, 'content')
    descriptor_path = _public_path_segments(
        strategy.descriptor, 'descriptor', allow_empty=True,
    )
    source_descriptor_path = _public_path_segments(
        strategy.source_descriptor, 'source_descriptor',
    )
    return OrderedFold(
        content=Ref(content_model),
        descriptor=Ref(content_model, descriptor_path),
        source=Ref(source_model),
        source_descriptor=Ref(source_model, source_descriptor_path),
        order=_public_ref(source_model, strategy.order, 'order'),
        polarity=_bind_public_polarity(source_model, strategy.polarity),
        mask=_public_ref(source_model, strategy.mask, 'mask'),
        trustee=_public_ref(source_model, strategy.trustee, 'trustee'),
        token=_bind_public_flat_token(strategy.token),
        domain=strategy.domain,
    )


@dataclass(frozen=True, slots=True)
class FoldPlan:
    """Fold-only plan. ``records`` is always empty (no mixed family)."""

    records: tuple = ()
    permission_model: type | None = None
    strategy: object | None = None

    def content_exists(self, user, permission):
        user = _require_instance(user, 'user')
        permission = _bind_terminal(permission, 'permission')
        if self.strategy is None:
            return None
        return OrderedFoldAllowed(self.strategy, user, permission)

    def common_permissions(self, user, content):
        from django.db.models import Exists, OuterRef

        user = _require_instance(user, 'user')
        if self.strategy is None or self.permission_model is None:
            if self.permission_model is None:
                return ()
            return self.permission_model._default_manager.none()
        qs = candidate_queryset(content)
        exists = self.content_exists(user, OuterRef(OuterRef('pk')))
        if exists is None:
            return self.permission_model._default_manager.none()
        return self.permission_model._default_manager.filter(
            Exists(qs),
        ).exclude(
            Exists(qs.filter(~Q(exists))),
        ).distinct()

    def permissions(self, user, content):
        from django.db.models import Exists, OuterRef

        user = _require_instance(user, 'user')
        content = _require_instance(content, 'content')
        if self.strategy is None or self.permission_model is None:
            if self.permission_model is None:
                return ()
            return self.permission_model._default_manager.none()
        exists = self.content_exists(user, OuterRef('pk'))
        if exists is None:
            return self.permission_model._default_manager.none()
        return self.permission_model._default_manager.filter(
            Exists(
                content._meta.concrete_model._default_manager.filter(
                    pk=content.pk,
                ).filter(exists)
            )
        ).distinct()

    def has_permission(self, user, content, permission):
        user = _require_instance(user, 'user')
        content = _require_instance(content, 'content')
        permission = _require_instance(permission, 'permission')
        if permission._meta.concrete_model is not self.permission_model:
            return False
        exists = self.content_exists(user, permission)
        if exists is None:
            return False
        return content._meta.concrete_model._default_manager.filter(
            pk=content.pk,
        ).filter(exists).exists()

    def filter_content(self, queryset, user, permission):
        exists = self.content_exists(user, permission)
        if exists is None:
            return queryset.none()
        return queryset.filter(exists).distinct()


class OrderedFoldQueryCompiler(QueryCompiler):
    """Compile one OrderedFold Allowed predicate. Group projection is None."""

    historical_fallback = False

    def applies(self, plan):
        return getattr(plan, 'strategy', None) is not None

    def complete_exists(self, plan, candidates, user, permission):
        content_exists = getattr(plan, 'content_exists', None)
        if callable(content_exists):
            return content_exists(user, permission)
        strategy = getattr(plan, 'strategy', None)
        if strategy is None:
            return None
        return OrderedFoldAllowed(strategy, user, permission)

    def group_exists(self, plan, candidates, user, permission):
        return None


class OrderedFoldRegistry(object):
    """Path-owned store of compiled OrderedFold plans and named filters."""

    def __init__(self):
        from trusts.conditions._ir import (
            ConditionRegistry,
            RegistryConditionLookup,
        )

        self._strategies = {}
        self._strategy_order = []
        self._frozen = False
        self._condition_lookup = None
        self.conditions = ConditionRegistry()
        self.set_condition_lookup(RegistryConditionLookup(self))

    @property
    def frozen(self):
        return self._frozen

    @property
    def condition_lookup(self):
        return self._condition_lookup

    def set_condition_lookup(self, lookup):
        if lookup is None:
            self._condition_lookup = None
            return
        record_for = getattr(lookup, 'record_for', None)
        compile_q = getattr(lookup, 'compile_q', None)
        if not callable(record_for) or not callable(compile_q):
            raise TrustsConfigurationError(
                'ConditionLookup must provide record_for and compile_q; '
                'no partial bind.'
            )
        self._condition_lookup = lookup

    def register_permission_condition(self, model, cond_code, condition):
        if self._frozen:
            raise TrustsConfigurationError(
                'Cannot register a permission condition on a frozen '
                'OrderedFoldRegistry.'
            )
        return self.conditions.register_permission_condition(
            model, cond_code, condition,
        )

    def get_permission_condition_record(self, model, cond_code):
        return self.conditions.get_permission_condition_record(
            model, cond_code,
        )

    def iter_permission_conditions(self):
        return self.conditions.iter_permission_conditions()

    def compile_registered_condition_q(self, model, perm, user):
        return self.conditions.compile_registered_condition_q(
            model, perm, user,
        )

    def evaluate_permission_condition(self, model, cond_code, user, perm, obj):
        return self.conditions.evaluate_permission_condition(
            model, cond_code, user, perm, obj,
        )

    def freeze(self):
        self._frozen = True

    @property
    def records(self):
        return ()

    @property
    def strategies(self):
        return tuple(self._strategy_order)

    def register_strategy(self, strategy):
        """Register one closed OrderedFold plan. Zero SQL.

        Frozen instances raise before validation or mutation. Duplicate
        OrderedFold on the same content terminal is a conflict and
        leaves the store unchanged.
        """
        if self._frozen:
            raise TrustsConfigurationError(
                'Cannot register on a frozen OrderedFoldRegistry.'
            )
        compiled = validate_ordered_fold(strategy)
        content_model = compiled.content_model
        if content_model in self._strategies:
            raise TrustsConfigurationError(
                'Conflicting OrderedFold registration for content terminal '
                '%s.' % content_model._meta.label
            )
        self._strategies[content_model] = compiled
        self._strategy_order.append(compiled)
        return compiled

    def plan_for(self, content, *, user=None, permission=None):
        content_model = _content_model(content)
        user_model = None
        if user is not None:
            user_model = _concrete_model(_require_instance(user, 'user'))
        permission_model = None
        if permission is not None:
            permission_model = _concrete_model(
                _require_instance(permission, 'permission')
            )

        strategy = self._strategies.get(content_model)
        if strategy is not None:
            if user_model is not None and user_model is not strategy.user_model:
                strategy = None
            if (
                permission_model is not None
                and permission_model is not strategy.permission_model
            ):
                strategy = None

        plan_permission = permission_model
        if strategy is not None:
            if plan_permission is None:
                plan_permission = strategy.permission_model
            elif plan_permission is not strategy.permission_model:
                raise TrustsConfigurationError(
                    'Applicable registrations must share one permission '
                    'model; got %s and %s.'
                    % (
                        plan_permission._meta.label,
                        strategy.permission_model._meta.label,
                    )
                )
        return FoldPlan(
            records=(),
            permission_model=plan_permission,
            strategy=strategy,
        )

    def permissions_for(self, user, content):
        user = _require_instance(user, 'user')
        content = _require_instance(content, 'content')
        return self.plan_for(content, user=user).permissions(user, content)

    def has_permission(self, user, content, permission):
        user = _require_instance(user, 'user')
        content = _require_instance(content, 'content')
        permission = _require_instance(permission, 'permission')
        return self.plan_for(
            content, user=user, permission=permission,
        ).has_permission(user, content, permission)

    def filter_authorized(self, queryset, user, permission):
        if not isinstance(queryset, QuerySet):
            raise TrustsConfigurationError(
                'filter_authorized requires a QuerySet, not %r.' % (queryset,)
            )
        user = _require_instance(user, 'user')
        permission = _require_instance(permission, 'permission')
        return self.plan_for(
            queryset, user=user, permission=permission,
        ).filter_content(queryset, user, permission)


@dataclass(frozen=True, slots=True)
class OrderedFoldBackendHandle:
    """Exact configured path, fold registry identity, and fold compiler."""

    path: str
    registry: object
    compiler: object

    def register_ordered_fold(self, source_model, fold):
        """Donate one OrderedFold plan on this backend.

        Provisional API: this method is excluded from the normal 1.x
        compatibility guarantee. Its signature or location may change, or it
        may be removed, in a future feature release.

        The positional ``source_model`` is the source root. Public
        ``fold.content`` is the content model class. ``descriptor`` is
        a Django ``__`` path on that content model and may be ``""``.
        ``source_descriptor``, ``order``, ``mask``, ``trustee``, and
        ``PolarityMap.field`` are Django ``__`` paths on the source.
        ``FlatToken.principal`` and optional ``member`` are independent
        model classes. Passing a ``Ref`` is ``TypeError``. A frozen
        backend raises ``TrustsConfigurationError`` before path parsing.
        """
        if getattr(self.registry, 'frozen', False):
            raise TrustsConfigurationError(
                'Cannot register on a frozen OrderedFoldRegistry.'
            )
        if isinstance(source_model, Ref):
            raise TypeError(
                'register_ordered_fold source must be a Django model '
                'class, not a Ref.'
            )
        if not _is_model_class(source_model):
            raise TrustsConfigurationError(
                'register_ordered_fold source must be a Django model '
                'class, not %r.' % (source_model,)
            )
        return self.registry.register_strategy(
            bind_public_ordered_fold(source_model, fold),
        )

    def add_named_filter(self, model, code, predicate):
        """Bind a named restricting predicate on this backend.

        Forwards the current registration-time permission-condition
        builder. A frozen/finalized backend raises
        ``TrustsConfigurationError`` before ``predicate`` is invoked.
        A prebuilt ``Expr`` is not accepted. The filter grants nothing
        independently.
        """
        if getattr(self.registry, 'frozen', False):
            raise TrustsConfigurationError(
                'Cannot register a permission condition on a frozen '
                'OrderedFoldRegistry.'
            )
        return self.registry.register_permission_condition(
            model, code, predicate,
        )

    @property
    def historical_fallback(self):
        return bool(getattr(self.compiler, 'historical_fallback', False))


def register_ordered_fold(backend, source, fold):
    """Donate one OrderedFold plan through the extension-owned registration path.

    Provisional API: this function is excluded from the normal 1.x
    compatibility guarantee. Its signature or location may change, or it
    may be removed, in a future feature release.

    Validates (zero SQL), compiles an immutable strategy, and stores it
    on the OrderedFold registry owned by ``backend``. Does not call
    Core ``BackendHandle.register_ordered_fold``.
    """
    from trusts_ordered_fold import checks as _checks  # noqa: F401

    if not isinstance(backend, OrderedFoldBackendHandle):
        registry = getattr(backend, 'registry', None)
        if not isinstance(registry, OrderedFoldRegistry):
            raise TrustsConfigurationError(
                'register_ordered_fold requires an OrderedFold backend '
                'handle; got %r. List TrustsOrderedFoldModelBackend and '
                'register through that path.'
                % (type(backend).__name__,)
            )
        register = getattr(backend, 'register_ordered_fold', None)
        if not callable(register):
            raise TrustsConfigurationError(
                'register_ordered_fold requires an OrderedFold backend '
                'handle; got %r.' % (type(backend).__name__,)
            )
        return register(source, fold)
    return backend.register_ordered_fold(source, fold)
