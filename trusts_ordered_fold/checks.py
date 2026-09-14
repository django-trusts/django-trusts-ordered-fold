"""System check ``trusts_ordered_fold.E001`` — PostgreSQL vendor gate.

Importing this module registers the check. The public package root and
``register_ordered_fold`` import this module so the diagnostic is
unavoidable without ``INSTALLED_APPS``.
"""

from django.core import checks as django_checks


CHECK_ID_ORDERED_FOLD_RENDERER = 'trusts_ordered_fold.E001'

_E001_HINT = (
    'Silencing this check ID suppresses only the early diagnostic. '
    'OrderedFold still fail-closes on the actual query connection; '
    'there is no fallback grant.'
)


def _live_ordered_fold_strategies(config):
    from trusts.core import TrustsCompilerError, TrustsConfigurationError

    if getattr(config, '_authorization_family', 'relationship') != 'ordered_fold':
        return []
    found = []
    try:
        paths = config._configured_trusts_paths()
    except TrustsConfigurationError:
        return found
    for path in paths:
        try:
            handle = config.configured_backend(path)
        except (TrustsConfigurationError, TrustsCompilerError):
            continue
        found.extend(getattr(handle.registry, 'strategies', ()))
    return found


@django_checks.register(django_checks.Tags.database)
def check_ordered_fold_renderer(app_configs, **kwargs):
    """Report selected aliases that cannot render live OrderedFold plans.

    Honors Django's ``databases`` argument exactly. ``None`` or empty
    opens no connections, executes no SQL, and is not an all-clear.
    Isolated ``OrderedFoldRegistry()`` instances are not scanned.
    Relationship-family configs are not scanned. The vendor gate uses
    connection metadata only (zero SQL).
    """
    databases = kwargs.get('databases')
    if not databases:
        return []

    from django.db import connections

    from trusts.apps import implementation_configs
    from trusts_ordered_fold.engine import ordered_fold_connection_supported

    owners = implementation_configs()
    if not owners:
        return []
    strategies = []
    for config in owners:
        strategies.extend(_live_ordered_fold_strategies(config))
    if not strategies:
        return []

    messages = []
    for alias in databases:
        connection = connections[alias]
        engine = (getattr(connection, 'settings_dict', None) or {}).get('ENGINE')
        vendor = getattr(connection, 'vendor', None)
        if ordered_fold_connection_supported(connection):
            continue
        messages.append(django_checks.Error(
            'Database alias %r (ENGINE=%s, vendor=%s) cannot render '
            'OrderedFold remaining-bits: PostgreSQL is required.'
            % (alias, engine, vendor),
            hint=_E001_HINT,
            obj=None,
            id=CHECK_ID_ORDERED_FOLD_RENDERER,
        ))
    return messages
