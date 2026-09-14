# django-trusts-ordered-fold

PostgreSQL ordered allow/deny authorization backend for django-trusts.

This P1 package is a **provisional façade**. It re-exports Core's current
OrderedFold construction types and forwards registration to Core's
`BackendHandle.register_ordered_fold`. The engine still lives in Core.
P2 will move the engine here and add `TrustsOrderedFoldModelBackend`.

Import root is `trusts_ordered_fold`. Do **not** import
`trusts.ordered_fold` from this package — that module remains Core-owned
until Core deletion.

## Install

```bash
pip install django-trusts-ordered-fold
```

`django-trusts` arrives as a dependency (`>=1.0.0.dev3,<2`). Until 1.x
is on PyPI, install Core from the pinned git revision used by this
package's CI. Do **not** add `'trusts'` or `'trusts_ordered_fold'` to
`INSTALLED_APPS`. This package ships no Django app in P1.

## Public surface

```python
from trusts_ordered_fold import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
    register_ordered_fold,
)

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

`register_ordered_fold(backend, source, fold)` forwards to
`backend.register_ordered_fold(source, fold)` on the current Core
handle. Registration-time validation, zero-SQL registration, exact-path
ownership, and freeze behavior are unchanged.

The five declaration types are the same objects Core exports today, so
`isinstance` checks in Core validation succeed.

## Supported versions

- Python 3.12, 3.13, and 3.14
- Django 6.1
- django-trusts 1.x, installed as a dependency and tested at Core
  `a8bacc7012b3d8d62d4b3245a9c63e44cbe733d0`

## Known limitations

- This façade is provisional and excluded from the normal 1.x
  compatibility guarantee. Signatures or location may change.
- P1 does not ship `TrustsOrderedFoldModelBackend`, the PostgreSQL
  renderer, or `trusts_ordered_fold.E001`. Those arrive in P2.
- OrderedFold evaluation remains PostgreSQL-only in Core. There is no
  OrderedFold-on-SQLite support.
- Do not copy or import Core renderer helpers
  (`OrderedFoldAllowed`, `RegisteredStrategy`,
  `ordered_fold_connection_supported`).

## Migration and API

- [migrates.md](migrates.md) — old/new imports and migration-bot checklist
- [django-trusts](https://github.com/django-trusts/django-trusts) — core library
- [Issues](https://github.com/django-trusts/django-trusts-ordered-fold/issues)

Contributor and pairing notes live in [DEV.md](DEV.md).

Licensed under the BSD 2-Clause License. Copyright BeeDesk, Inc.
