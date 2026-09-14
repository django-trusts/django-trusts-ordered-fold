# migrates.md — django-trusts-ordered-fold 1.0.0.dev0

This file is the **P2 engine + backend** route. The engine lives in this
package. Pair against Core C2
`72b41a0cd1d3746ac0eb82ad220eec9b559d6f7b`, which deleted the
provisional Core shims.

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
| Implementation owner | relationship `TrustsImplementationConfig` | subclass `OrderedFoldImplementationConfig` (discriminator alone is not enough) |
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

The five declaration types are **extension-owned**. C2 deleted the
Core re-exports (`trusts.core.OrderedFold` and siblings) and
`BackendHandle.register_ordered_fold`. Register through this package's
function and handle.

`trusts.ordered_fold` is deleted from Core. Importing it is
`ModuleNotFoundError`. Do not reclaim that path.

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
| Family-local `authorization_required` | Runtime fail-closed (zero SQL) when there is no `auth.Permission` fold plan, the object `pk` is missing, or the request user has no primary key. Core `trusts.E008` scans only Core decorator declarations and relationship-family handles; this slice does **not** register `trusts_ordered_fold.E002` |
| Family-local `common_permissions` | Fold-family handles only; relationship handles are omitted |
| Core kernel suite at the C2 pin | Unchanged (this package does not edit Core) |

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
- [ ] Pin Core at C2 `72b41a0cd1d3746ac0eb82ad220eec9b559d6f7b` on `DEV_standalone_ordered_fold`.
- [ ] Replace `from trusts.core import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` with `from trusts_ordered_fold import …`.
- [ ] Replace `backend.register_ordered_fold(source, fold)` call sites with `register_ordered_fold(backend, source, fold)`.
- [ ] List `trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend` (or a subclass) in `AUTHENTICATION_BACKENDS`.
- [ ] Own that path by subclassing `OrderedFoldImplementationConfig`. Do not set `_authorization_family = 'ordered_fold'` alone on Core `TrustsImplementationConfig`; that still creates `TrustsRegistry` / `BackendHandle` and `register_ordered_fold()` rejects it.
- [ ] Import family-local `authorization_required` and `common_permissions` from `trusts_ordered_fold`. Guard completeness is runtime fail-closed; Core `trusts.E008` does not see fold declarations, and this slice does not register `trusts_ordered_fold.E002`.
- [ ] Do not import `trusts.ordered_fold`. Core C2 deleted that module (`ModuleNotFoundError`).
- [ ] Confirm the five types are extension-owned (not Core `is` identity).
- [ ] Confirm registration acceptance, rejection, freeze, exact-path isolation, and 0 SQL against Core `72b41a0cd1d3746ac0eb82ad220eec9b559d6f7b`.
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
- [ ] Leftover Core `register_ordered_fold` callers fail loud (`AttributeError`). Windows W owns the AccessCheck floor; this slice does not redesign Windows.
- [ ] Silenced `trusts.E006` becomes `trusts_ordered_fold.E001`; silencing still does not create a fallback grant.
- [ ] Confirm `pip` refuses core below `1.0.0.dev3` against this wheel.
- [ ] Leave package version at `1.0.0.dev0` and core floor at `1.0.0.dev3`.
