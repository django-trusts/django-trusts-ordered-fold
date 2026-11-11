# django-trusts-ordered-fold

PostgreSQL ordered allow/deny authorization backend for django-trusts.

This package is a provisional backend for ordered allow and deny.
Import root is `trusts_ordered_fold`. The application registers the
trust with `register()`. For one saved object, `has_perm` walks the
content's ACE rows in order and clears a permission's bits.

## Install

```bash
pip install django-trusts-ordered-fold
```

`django-trusts` arrives as a dependency (`>=1.0.0.dev3,<2`). Until 1.x
is on PyPI, install Core from the git revision pinned in this
package's CI. Do **not** add `'trusts'` or `'trusts_ordered_fold'` to
`INSTALLED_APPS`. The host app extends `TrustsConfigMixin`. A subclass
of `TrustsOrderedFoldModelBackend` sets `query_compiler` and is listed
in `AUTHENTICATION_BACKENDS`.

## Public surface

```python
from trusts_ordered_fold import (
    OrderedFoldQueryCompiler,
    TrustsOrderedFoldModelBackend,
)

class DocumentFoldBackend(TrustsOrderedFoldModelBackend):
    query_compiler = OrderedFoldQueryCompiler(
        order='ace_order',
        polarity='ace_type',
        allow=1,
        deny=2,
        mask='access_mask',
        trustee='user',
        masks=(('read', 0x1), ('write', 0x2), ('readwrite', 0x3)),
    )

# register() is the application's normal trust registration:
# registry.register(
#     trust=Ace, user='user', permission='permission', content='document',
# )
```

`has_perm(user, perm, obj)` for one saved object runs one PostgreSQL
statement. The permission codename maps to bits. ACE rows are walked
in `(order, pk)` order. An allow row clears its bits from what remains.
A deny row that touches a remaining bit denies. The check grants when
every requested bit is cleared. One ACE can cover several permissions.
A NULL order, NULL polarity, NULL mask, NULL trustee, negative mask, or
any other polarity on that content denies, including a row for another
trustee. On any other database the object check denies and does not
emit fold SQL.

## Supported versions

- Python 3.12, 3.13, and 3.14
- Django 6.1
- django-trusts 1.x, installed from the experiment branch pinned in CI

## Known limitations

- This surface is provisional and excluded from the normal 1.x
  compatibility guarantee.
- Only `has_perm` for one saved object is folded. `.permitted()` and
  `get_permitted_users` contribute nothing, so they do not grant.
- A queryset check, a second registration, an `along=` walk, and a
  `via=` walk are not folded. They deny.
- Descriptor equality (an ACE and an object that share a key, with no
  path from the ACE to the object) is not a `register()` content path.
- A token whose principal is not a field path on the ACE is configured
  on the compiler. Multi-hop token paths and `to_field` collisions are
  not covered.
- Do not import `trusts.ordered_fold` or `register_ordered_fold`.

## Migration and API

- [migrates.md](migrates.md) — old/new imports and migration-bot checklist
- [django-trusts](https://github.com/django-trusts/django-trusts) — core library
- [Issues](https://github.com/django-trusts/django-trusts-ordered-fold/issues)

Contributor and pairing notes live in [DEV.md](DEV.md).

Licensed under the BSD 2-Clause License. Copyright BeeDesk, Inc.
