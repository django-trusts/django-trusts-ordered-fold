# django-trusts-ordered-fold

PostgreSQL ordered allow/deny authorization backend for django-trusts.

This package owns the OrderedFold engine and the concrete
`TrustsOrderedFoldModelBackend`. Import root is `trusts_ordered_fold`.
Do **not** import `trusts.ordered_fold` — Core C2 deleted that module.

## Install

```bash
pip install django-trusts-ordered-fold
```

`django-trusts` arrives as a dependency (`>=1.0.0.dev3,<2`). Until 1.x
is on PyPI, install Core from the pinned git revision used by this
package's CI. Do **not** add `'trusts'` or `'trusts_ordered_fold'` to
`INSTALLED_APPS`. List `TrustsOrderedFoldModelBackend` (or a subclass)
in `AUTHENTICATION_BACKENDS` and own that path by subclassing
`OrderedFoldImplementationConfig`. Setting `_authorization_family =
'ordered_fold'` on a plain `TrustsImplementationConfig` is not enough:
Core's `_create_registry()` / `_create_handle()` still produce
`TrustsRegistry` / `BackendHandle`, and `register_ordered_fold()`
rejects those types.

## Public surface

```python
from trusts_ordered_fold import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    OrderedFoldImplementationConfig,
    PermissionMaskDomain,
    PolarityMap,
    TrustsOrderedFoldModelBackend,
    register_ordered_fold,
)

# AUTHENTICATION_BACKENDS includes
# 'trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend'

register_ordered_fold(backend, Ace, OrderedFold(
    content=Document,
    descriptor='',
    source_descriptor='document',
    order='ace_order',
    polarity=PolarityMap('ace_type', allow_value=ALLOW, deny_value=DENY),
    mask='access_mask',
    trustee='user',
    token=FlatToken(
        principal=User,
        principal_user='',
        principal_identity='',
    ),
    domain=PermissionMaskDomain(Permission, (
        MaskEntry('read', 0x1),
    )),
))
```

`register_ordered_fold(backend, source, fold)` validates (zero SQL),
compiles an immutable strategy, and stores it on the OrderedFold
registry for that exact backend path. It does not call Core
`BackendHandle.register_ordered_fold`.

Importing this package registers system check `trusts_ordered_fold.E001`
without requiring `INSTALLED_APPS`. Silencing the check does not create
a fallback grant. An applicable fold on a non-PostgreSQL connection
raises `TrustsConfigurationError`.

## Supported versions

- Python 3.12, 3.13, and 3.14
- Django 6.1
- django-trusts 1.x, installed as a dependency and tested at Core
  `b2ad8aa052eef25fd05a79b2dfba7b7049af148d`

## Known limitations

- This surface is provisional and excluded from the normal 1.x
  compatibility guarantee. Signatures or location may change.
- OrderedFold evaluation is PostgreSQL-only. There is no
  OrderedFold-on-SQLite support.
- Group projection is unsupported.
- Mixed relationship/OrderedFold QuerySet and common-permission
  combination is not a 1.0 contract. Object-level `User.has_perm` uses
  Django's ordered backend OR across families.
- Do not import deleted Core fold names (`trusts.ordered_fold`,
  `from trusts.core import OrderedFold`, or Core renderer helpers
  `OrderedFoldAllowed`, `RegisteredStrategy`,
  `ordered_fold_connection_supported`). Those live only on this
  package, and the renderer helpers are not public.

## Migration and API

- [migrates.md](migrates.md) — old/new imports and migration-bot checklist
- [django-trusts](https://github.com/django-trusts/django-trusts) — core library
- [Issues](https://github.com/django-trusts/django-trusts-ordered-fold/issues)

Contributor and pairing notes live in [DEV.md](DEV.md).

Licensed under the BSD 2-Clause License. Copyright BeeDesk, Inc.
