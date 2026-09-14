# migrates.md — django-trusts-ordered-fold 1.0.0.dev0

This file is the **P2 engine + backend** route. The engine lives in this
package. Core still ships shims at
`6934894489d4fc0e46de88b55b9a27f5f2eb2b41` until C2.

Do **not** add `'trusts'` or `'trusts_ordered_fold'` to
`INSTALLED_APPS`. Core is a Python library. This package ships no
Django app; host apps subclass `OrderedFoldImplementationConfig`.

## Audience

- **Applications that constructed OrderedFold on Core or the P1 façade:**
  retarget the five construction types and `register_ordered_fold` to
  `trusts_ordered_fold`, list `TrustsOrderedFoldModelBackend`, and
  donate through an OrderedFold handle.
- **Windows ACL:** wait for the W slice. Do not list this backend beside
  `WinfsBackend` for the same objects.

## P2 import, backend, and check

| Surface | Old (Core / P1) | New (`django-trusts-ordered-fold==1.0.0.dev0`) |
| --- | --- | --- |
| Package | `django-trusts` only, or P1 façade over Core | `django-trusts` + `django-trusts-ordered-fold` |
| Import root | `trusts.core` / `trusts.ordered_fold` | **`trusts_ordered_fold`** |
| Declarations | `from trusts.core import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` | `from trusts_ordered_fold import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` |
| Registration | `backend.register_ordered_fold(source, fold)` or P1 forwarder onto Core | `register_ordered_fold(backend, source, fold)` on an **OrderedFold** handle |
| Handle | Core `BackendHandle` + `TrustsRegistry` | `OrderedFoldBackendHandle` + `OrderedFoldRegistry` |
| Concrete backend | n/a (P1) | **`trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend`** in `AUTHENTICATION_BACKENDS` |
| Implementation owner | relationship `TrustsImplementationConfig` | `_authorization_family = 'ordered_fold'` via `OrderedFoldImplementationConfig` |
| Vendor check | Core `trusts.E006` | **`trusts_ordered_fold.E001`** (registered on package import) |
| Engine / PostgreSQL renderer | `trusts.ordered_fold` | this package (`trusts_ordered_fold.engine`) |
| QuerySet / guard / common-permission | Core aggregates (relationship-family after C1) | `trusts_ordered_fold.granted`, `AuthorizedQuerySet`, `authorization_required`, `common_permissions` |

```python
# Old (Core provisional / P1 façade)
from trusts.core import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
)
backend.register_ordered_fold(Ace, OrderedFold(...))

# New (P2)
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
register_ordered_fold(backend, Ace, OrderedFold(...))
```

The five declaration types are **extension-owned**. They are not the
same objects as Core's remaining shims. Register through this package's
function and handle; do not call Core `BackendHandle.register_ordered_fold`.

Do **not** import `trusts.ordered_fold` from this package. That module
path stays Core-owned until C2. Do not reclaim it during coexistence.

## Behavior in P2

| Situation | Result |
| --- | --- |
| Valid public fold on an unfrozen OrderedFold handle | Registers; 0 SQL; compiled strategy stored on that handle's registry only |
| Core `BackendHandle` / `TrustsRegistry` | `TrustsConfigurationError`; store unchanged |
| `Ref` source or `Ref` fold fields | `TypeError`; store unchanged |
| Derived `source=` on the public `OrderedFold` | `TrustsConfigurationError`; store unchanged |
| Not an `OrderedFold` | `TrustsConfigurationError`; store unchanged |
| Frozen / finalized registry | `TrustsConfigurationError` **before** path parsing / validation |
| Second exact backend path | Independent registry; no leak |
| Missing / malformed / wrong-vendor policy | Fail closed (`TrustsConfigurationError`) |
| Registration validation / inapplicability | Zero SQL |
| Applicable evaluation | One authorization SQL per backend invocation |
| Named filter | Restricts a grant; never creates one |
| Group projection | Unsupported (`group_exists` is `None`) |
| Mixed relationship/OrderedFold QuerySet or common-permission | **Not a 1.0 contract** |
| Object `User.has_perm` across listed backends | Django ordered backend OR |
| Applicable fold, vendor ≠ PostgreSQL | `TrustsConfigurationError` when the fold backend is reached |
| `trusts_ordered_fold.E001` | Blocks deployment on non-PostgreSQL aliases with a live fold |
| Silenced E001 | Does **not** create a fallback grant |
| Core kernel suite at the C1 pin | Unchanged (this package does not edit Core) |

## Migration-bot checklist

Search application code, Windows, GH, Zero, and docs for Core fold
imports and the new package root:

```text
from trusts.core import OrderedFold
from trusts.core import PermissionMaskDomain
from trusts.core import MaskEntry
from trusts.core import PolarityMap
from trusts.core import FlatToken
from trusts.ordered_fold import
import trusts.ordered_fold
backend.register_ordered_fold(
handle.register_ordered_fold(
.registry.register_strategy(
register_strategy(
OrderedFold(
trusts.ordered_fold
trusts.E006
SILENCED_SYSTEM_CHECKS.*E006
AnyPath and OrderedFold cannot share one terminal
already has an OrderedFold strategy
from trusts_ordered_fold import
register_ordered_fold(
TrustsOrderedFoldModelBackend
trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend
OrderedFoldImplementationConfig
trusts_ordered_fold.E001
SILENCED_SYSTEM_CHECKS.*E001
```

Then:

- [ ] Install `django-trusts-ordered-fold` (it requires `django-trusts>=1.0.0.dev3,<2`).
- [ ] Pin Core at C1 `6934894489d4fc0e46de88b55b9a27f5f2eb2b41` or later on `DEV_standalone_ordered_fold`.
- [ ] Replace `from trusts.core import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` with `from trusts_ordered_fold import …`.
- [ ] Replace `backend.register_ordered_fold(source, fold)` call sites with `register_ordered_fold(backend, source, fold)`.
- [ ] List `trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend` (or a subclass) in `AUTHENTICATION_BACKENDS`.
- [ ] Own that path from `OrderedFoldImplementationConfig` (or a config with `_authorization_family = 'ordered_fold'`).
- [ ] Do not import `trusts.ordered_fold` from this package. Leave that module to Core until C2.
- [ ] Confirm the five types are extension-owned (not Core `is` identity).
- [ ] Confirm registration acceptance, rejection, freeze, exact-path isolation, and 0 SQL against Core `6934894489d4fc0e46de88b55b9a27f5f2eb2b41`.
- [ ] Confirm applicable evaluation is one authorization SQL and inapplicable is 0 SQL.
- [ ] Confirm named filters restrict and never create a grant.
- [ ] Confirm unsupported vendors raise `TrustsConfigurationError` when the fold backend is reached.
- [ ] Confirm `trusts_ordered_fold.E001` reports non-PostgreSQL aliases with a live fold.
- [ ] Do not add `'trusts'` or `'trusts_ordered_fold'` to `INSTALLED_APPS`.
- [ ] Do not register relationships on an OrderedFold handle.
- [ ] Do not add a Core dependency on this package.
- [ ] Do not open a Core or Windows PR in this slice.
- [ ] Detect remaining Core fold imports (`trusts.core` fold names, `trusts.ordered_fold`, `.register_strategy(`).
- [ ] Detect single-backend mixed relationship+fold registration that assumed `#187` same-plan OR; this slice requires an OrderedFold backend path.
- [ ] Drop XOR / `#187` workarounds that assumed one plan.
- [ ] Windows `compat` floor still accepts Core `register_ordered_fold` until W.
- [ ] Silenced `trusts.E006` becomes `trusts_ordered_fold.E001`; silencing still does not create a fallback grant.
- [ ] Confirm `pip` refuses core below `1.0.0.dev3` against this wheel.
- [ ] Leave package version at `1.0.0.dev0` and core floor at `1.0.0.dev3`.
