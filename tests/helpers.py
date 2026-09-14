"""Isolated OrderedFold fixtures for registration and engine proofs."""

from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db import connection, models

from trusts_ordered_fold import (
    AuthorizedManager,
    FlatToken,
    MaskEntry,
    OrderedFold,
    OrderedFoldBackendHandle,
    OrderedFoldQueryCompiler,
    OrderedFoldRegistry,
    PermissionMaskDomain,
    PolarityMap,
)

ALLOW = 1
DENY = 2


@contextmanager
def tables(*model_classes):
    with connection.schema_editor() as editor:
        for model in model_classes:
            editor.create_model(model)
    try:
        yield
    finally:
        with connection.schema_editor() as editor:
            for model in reversed(model_classes):
                editor.delete_model(model)


def handle(registry=None, path='tests.ordered-fold.handle-a'):
    if registry is None:
        registry = OrderedFoldRegistry()
    return OrderedFoldBackendHandle(
        path=path,
        registry=registry,
        compiler=OrderedFoldQueryCompiler(),
    )


def live_fold_config(apps_registry=None):
    """The installed OrderedFold implementation owner."""
    from tests.fold_host.apps import FoldHostConfig
    from trusts.apps import implementation_configs
    from trusts.core import TrustsConfigurationError

    configs = implementation_configs(apps_registry)
    hosts = [config for config in configs if type(config) is FoldHostConfig]
    if len(hosts) == 1:
        return hosts[0]
    folds = [
        config for config in configs
        if getattr(config, '_authorization_family', None) == 'ordered_fold'
    ]
    if len(folds) == 1:
        return folds[0]
    raise TrustsConfigurationError(
        'live_fold_config() needs exactly one OrderedFold owner; got %r'
        % (configs,)
    )


def isolate_live_registry(config, registry, path=None):
    """Swap a standalone registry into the live store without freezing."""
    if path is None:
        paths = config._configured_trusts_paths()
        path = paths[0]
    config.registries[path] = registry
    return registry


def direct_models(*, suffix=''):
    User = get_user_model()
    Permission = type('Permission%s' % suffix, (models.Model,), {
        '__module__': __name__,
        'codename': models.CharField(max_length=64),
        'Meta': type('Meta', (), {'app_label': 'trusts_ordered_fold_tests'}),
    })
    Document = type('Document%s' % suffix, (models.Model,), {
        '__module__': __name__,
        'title': models.CharField(max_length=40),
        'objects': AuthorizedManager(),
        'Meta': type('Meta', (), {'app_label': 'trusts_ordered_fold_tests'}),
    })
    Ace = type('Ace%s' % suffix, (models.Model,), {
        '__module__': __name__,
        'document': models.ForeignKey(Document, on_delete=models.CASCADE),
        'ace_order': models.IntegerField(),
        'ace_type': models.IntegerField(),
        'access_mask': models.BigIntegerField(),
        'user': models.ForeignKey(User, on_delete=models.CASCADE),
        'Meta': type('Meta', (), {'app_label': 'trusts_ordered_fold_tests'}),
    })
    return Permission, Document, Ace


def public_direct_fold(Ace, Permission, Document, *, token=None):
    User = get_user_model()
    if token is None:
        token = FlatToken(
            principal=User,
            principal_user='',
            principal_identity='',
        )
    return OrderedFold(
        content=Document,
        descriptor='',
        source_descriptor='document',
        order='ace_order',
        polarity=PolarityMap('ace_type', allow_value=ALLOW, deny_value=DENY),
        mask='access_mask',
        trustee='user',
        token=token,
        domain=PermissionMaskDomain(Permission, (
            MaskEntry('read', 0x1),
            MaskEntry('write', 0x2),
            MaskEntry('readwrite', 0x3),
        )),
    )
